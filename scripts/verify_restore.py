"""Restore a backup into a NEW isolated database and temp object directory.

Never touches the active database or starts a worker. Confirms all referenced
object hashes and immutable package ZIP integrity against the restored records.
"""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
import uuid
import zipfile
from pathlib import Path


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("backup")
    args = p.parse_args()
    root = Path(args.backup).resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    for name, digest in manifest["files"].items():
        if (
            name not in ("database.dump", "objects.tar")
            or hashlib.sha256((root / name).read_bytes()).hexdigest() != digest
        ):
            raise SystemExit("Backup checksum mismatch")
    database = "dove_restore_" + uuid.uuid4().hex[:12]
    base = ["docker", "compose", "exec", "-T", "db"]
    run(base + ["createdb", "-U", "dove", database])
    try:
        with (root / "database.dump").open("rb") as source:
            run(
                base
                + [
                    "pg_restore",
                    "-U",
                    "dove",
                    "-d",
                    database,
                    "--no-owner",
                    "--exit-on-error",
                ],
                stdin=source,
            )
        result = run(
            base
            + [
                "psql",
                "-U",
                "dove",
                "-d",
                database,
                "-At",
                "-c",
                "SELECT json_build_object('id',id,'kind',kind,'data',data)::text FROM records WHERE kind IN ('document','package') ORDER BY id",
            ],
            capture_output=True,
            text=True,
        )
        rows = [json.loads(line) for line in result.stdout.splitlines() if line]
        with tempfile.TemporaryDirectory(prefix="dove-restore-") as destination:
            out = Path(destination)
            with tarfile.open(root / "objects.tar") as archive:
                archive.extractall(out, filter="data")
            for row in rows:
                data = row["data"]
                path = (out / data["storage_key"]).resolve()
                if not path.is_relative_to(out):
                    raise SystemExit("Unsafe object path")
                content = path.read_bytes()
                expected = data.get("sha256", data.get("digest"))
                if hashlib.sha256(content).hexdigest() != expected:
                    raise SystemExit("Restored object hash mismatch")
                if row["kind"] == "package":
                    with zipfile.ZipFile(io.BytesIO(content)) as z:
                        if z.testzip():
                            raise SystemExit("Corrupt package ZIP")
            print(
                json.dumps(
                    {
                        "restoration": "passed",
                        "database": database,
                        "objects_verified": len(rows),
                        "worker_started": False,
                    }
                )
            )
    finally:
        # The name is generated here and only this disposable database is dropped.
        run(base + ["dropdb", "-U", "dove", database])


if __name__ == "__main__":
    main()
