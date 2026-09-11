"""Consistent paused application backup. Run from repo root; Docker must be up.

Backups are deliberately not committed. Encrypt before off-host storage.
"""

import argparse
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path
from datetime import datetime, timezone


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    args = p.parse_args()
    target = Path(args.output).resolve()
    if target.exists():
        raise SystemExit("Use a new backup directory; never overwrite a backup")
    target.mkdir(parents=True)
    run(["docker", "compose", "stop", "api", "worker"])
    try:
        with (target / "database.dump").open("wb") as out:
            run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "db",
                    "pg_dump",
                    "-U",
                    "dove",
                    "-d",
                    "dove",
                    "-Fc",
                ],
                stdout=out,
            )
        with (target / "objects.tar").open("wb") as out:
            run(
                [
                    "docker",
                    "compose",
                    "run",
                    "--rm",
                    "--no-deps",
                    "-T",
                    "api",
                    "tar",
                    "-C",
                    "/data/objects",
                    "-cf",
                    "-",
                    ".",
                ],
                stdout=out,
            )
        manifest = {
            "created": datetime.now(timezone.utc).isoformat(),
            "files": {
                name: hashlib.sha256((target / name).read_bytes()).hexdigest()
                for name in ("database.dump", "objects.tar")
            },
            "restore_worker_policy": "Keep paused until deletion ledger and uncertain sends are reviewed",
        }
        (target / "manifest.json").write_text(json.dumps(manifest, indent=2))
        print("Backup created at " + str(target))
    finally:
        run(["docker", "compose", "start", "api", "worker"])


if __name__ == "__main__":
    main()
