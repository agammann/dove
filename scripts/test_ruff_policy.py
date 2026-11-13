"""Check that narrowly scoped Ruff exceptions do not disable unrelated findings."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
source = """\
from fastapi import Depends, File
from random import random

def dependency():
    return 1

def endpoint(value=Depends(dependency), upload=File(...), unsafe=random()):
    return value, upload, unsafe

def catches_everything():
    try:
        raise RuntimeError("fixture")
    except Exception:
        return None

def wrong_type(value):
    if not isinstance(value, str):
        raise ValueError("fixture")

def unclosed_file():
    handle = open("fixture")
    return handle.read()
"""
with tempfile.TemporaryDirectory(prefix="dove-ruff-policy-") as directory:
    path = Path(directory) / "fixture.py"
    path.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--config", str(root / "ruff.toml"),
         "--output-format", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 1:
        raise AssertionError(f"Expected Ruff findings, got exit {result.returncode}: {result.stderr}")
    findings = json.loads(result.stdout)
    focused = [item for item in findings if item["code"] in {"B008", "BLE001", "SIM115", "TRY004"}]
    assert sorted(item["code"] for item in focused) == ["B008", "BLE001", "SIM115", "TRY004"]
    assert "random" in next(item["message"] for item in focused if item["code"] == "B008")
print("PASS: FastAPI declarations are allowed; unrelated default, broad-catch, file and type diagnostics remain active")
