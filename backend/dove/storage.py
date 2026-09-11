import hashlib
from pathlib import Path
from fastapi import HTTPException
from .config import settings
from .db import uid


def store(org, content):
    # Callers hold the organization transaction lock. Include orphaned files
    # after interrupted writes so a crash cannot refund the physical quota.
    objects = list((settings.storage_dir / org).glob("*"))
    size = sum(p.stat().st_size for p in objects if p.is_file())
    if (
        len(objects) >= settings.max_retained_objects_per_org
        or size + len(content) > settings.max_org_storage_bytes
    ):
        raise HTTPException(
            409,
            "Workspace storage allowance reached. Export and remove older work before adding files",
        )
    key = f"{org}/{uid()}"
    target = settings.storage_dir / key
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as f:
        f.write(content)
    return key, hashlib.sha256(content).hexdigest()


def read(org, key):
    root = settings.storage_dir.resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root / org):
        raise HTTPException(404, "File unavailable")
    return path.read_bytes()


def extract(filename, content, org="local"):
    if not content or len(content) > settings.max_upload_bytes:
        raise HTTPException(422, "Upload a non-empty PDF or TXT file, at most 8 MB")
    ext = Path(filename).suffix.lower()
    try:
        if ext == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise ValueError("File is not a PDF")
            from .pdf_process import process_pdf

            pages = process_pdf(org, content)["pages"]
        elif ext == ".txt":
            text = content.decode("utf-8-sig")
            if "\x00" in text:
                raise ValueError("Binary content is not a text file")
            pages = [text]
        else:
            raise ValueError("Only text-based PDF and UTF-8 TXT files are supported")
        if sum(len(p) for p in pages) > settings.max_text_chars:
            raise ValueError("Document exceeds 100,000 characters; split the document")
        if not any(p.strip() for p in pages):
            raise ValueError("No readable text. Upload a text-based PDF or TXT")
        return pages
    except HTTPException:
        raise
    except Exception as e:
        msg = (
            str(e)
            if isinstance(e, ValueError)
            else "Unreadable document. Export a text-based PDF or UTF-8 TXT and try again"
        )
        raise HTTPException(422, msg) from None
