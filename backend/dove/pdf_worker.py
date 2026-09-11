"""Disposable PDF processor. Production resource limits apply before parsing."""

import base64
import io
import json
import os
import sys


def main():
    if os.name == "posix":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    mode, page_arg, pages_arg, chars_arg = sys.argv[1:]
    content = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        raise ValueError("Upload exceeds 8 MB")
    if mode == "extract":
        from pypdf import PdfReader

        pdf = PdfReader(io.BytesIO(content), strict=True)
        if pdf.is_encrypted:
            raise ValueError("Upload an unencrypted readable PDF")
        if len(pdf.pages) > int(pages_arg):
            raise ValueError("PDF exceeds the page allowance; split the document")
        pages, count = [], 0
        for page in pdf.pages:
            text = page.extract_text() or ""
            count += len(text)
            if count > int(chars_arg):
                raise ValueError(
                    "Document exceeds the text allowance; split the document"
                )
            if len(text.strip()) < 10:
                raise ValueError(
                    "A page is scanned or unreadable. Upload a text-based PDF or TXT version; OCR is not supported"
                )
            pages.append(text)
        result = {"pages": pages}
    elif mode == "preview":
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(content) as document:
            page_no = int(page_arg)
            if not 0 <= page_no < len(document) <= int(pages_arg):
                raise ValueError("Preview page is out of range")
            page = document[page_no]
            scale = min(1.6, 1200 / max(page.get_width(), page.get_height()))
            output = io.BytesIO()
            page.render(scale=scale).to_pil().save(output, format="PNG")
            result = {
                "count": len(document),
                "png": base64.b64encode(output.getvalue()).decode(),
            }
    else:
        raise ValueError("Unsupported PDF operation")
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.stdout.write(json.dumps({"error": str(exc)}))
    except Exception:
        sys.stdout.write(
            json.dumps(
                {
                    "error": "Unreadable document. Export a text-based PDF or UTF-8 TXT and try again"
                }
            )
        )
