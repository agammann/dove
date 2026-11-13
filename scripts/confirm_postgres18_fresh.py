"""Initialize only a confirmed fresh, local Docker Compose installation."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def docker(args, *, env=None, capture=False):
    return subprocess.run(
        ["docker", *args], check=True, text=True,
        capture_output=capture, env=env,
    ).stdout


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("local", "production"):
        raise SystemExit("Choose exactly local or production.")
    if Path.cwd().resolve() != Path(__file__).resolve().parents[1]:
        raise SystemExit("Run this command from the repository root.")
    for key in os.environ:
        if re.match(r"^(COMPOSE_|DOCKER_HOST$|DOCKER_CONTEXT$)", key, re.I):
            raise SystemExit(f"Unset {key} and identify the intended Docker host and project first.")
    host = json.loads(docker(["context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"], capture=True))
    if not isinstance(host, str) or not re.match(r"^(unix://|npipe://)", host, re.I):
        raise SystemExit("A local Docker context is required; use a reviewed procedure for other hosts.")
    base = ["compose", "-p", "dove", "-f", "compose.yaml"]
    if sys.argv[1] == "production":
        base += ["-f", "compose.production.yaml"]
    existing = docker([*base, "ps", "-a", "--format", "json"], capture=True).strip()
    if existing and existing != "[]":
        raise SystemExit("This project already has containers. Stop and identify the existing installation.")
    print("This initializes a NEW database and object store; it does not migrate data.")
    print("Inventory all prior Dove databases, roles, object storage, projects, hosts and backups first.")
    print("The guard cannot discover storage outside the selected project. Stop all writers and storage changes.")
    if input("Type NO EXISTING DOVE DATA to confirm: ") != "NO EXISTING DOVE DATA":
        raise SystemExit("Fresh installation was not confirmed.")
    env = {**os.environ, "DOVE_PG18_FRESH_INSTALL": "confirmed-no-existing-dove-data"}
    docker([*base, "-f", "compose.postgres18-init.yaml", "up", "-d", "--wait", "--wait-timeout", "180", "db"], env=env)
    docker([*base, "up", "-d", "--force-recreate", "--wait", "--wait-timeout", "180", "db"], env=env)
    print("Fresh PostgreSQL 18 database initialized. Continue with the setup guide.")


if __name__ == "__main__":
    main()
