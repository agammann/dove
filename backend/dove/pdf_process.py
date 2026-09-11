"""Bounded admission and disposable PDF child processes, without provider secrets."""

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from fastapi import HTTPException
from .config import settings

_guard = threading.Lock()
_active = set()


def process_pdf(org, content, mode="extract", page=0):
    with _guard:
        if org in _active or len(_active) >= 2:
            raise HTTPException(
                429, "Document processing is busy. Please retry shortly"
            )
        _active.add(org)
    try:
        env = {
            k: v
            for k, v in os.environ.items()
            if k.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PATH"}
        }
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "dove.pdf_worker",
                mode,
                str(page),
                str(settings.max_document_pages),
                str(settings.max_text_chars),
            ],
            input=content,
            capture_output=True,
            timeout=settings.pdf_timeout_seconds,
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            check=True,
        )
        output = json.loads(result.stdout)
        if output.get("error"):
            raise HTTPException(422, output["error"])
        return output
    except (subprocess.SubprocessError, OSError, ValueError):
        raise HTTPException(
            422,
            "PDF processing exceeded its resource budget or could not finish. Split the document or upload a readable TXT version",
        ) from None
    finally:
        with _guard:
            _active.discard(org)
