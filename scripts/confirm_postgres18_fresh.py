"""Initialize only a confirmed fresh, local Docker Compose installation."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


def forbidden_selector(key):
    return bool(re.match(r"^(COMPOSE_.*|DOCKER_.*|DATABASE_URL|PG[A-Z0-9_]*|POSTGRES_USER|POSTGRES_DB|DOVE_PG18_FRESH_INSTALL)$", key, re.I))


def unsafe_dotenv_selector(content):
    for line in content.splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:=|$)", line)
        if match and forbidden_selector(match.group(1)):
            return match.group(1)
    return None


def automatic_override_present():
    return any(Path(name).exists() for name in ("compose.override.yaml", "compose.override.yml", "docker-compose.override.yaml", "docker-compose.override.yml"))


def docker(args, *, env=None, capture=False):
    return subprocess.run(
        ["docker", *args], check=True, text=True,
        capture_output=capture, env=env,
    ).stdout


def validate_config(config, mode):
    """Validate resolved values without returning or displaying credentials."""
    try:
        services = config["services"]
        db, api, worker = services["db"], services["api"], services["worker"]
        db_env, app_env = db["environment"], api["environment"]
        password = db_env["POSTGRES_PASSWORD"]
        if not re.fullmatch(r"[A-Za-z0-9_-]{24,}", password):
            raise ValueError("database password must be at least 24 URL-safe characters")
        if db["image"] != "postgres:18.4-alpine" or db_env["POSTGRES_USER"] != "dove" or db_env["POSTGRES_DB"] != "dove":
            raise ValueError("unexpected database image, user or database")
        if app_env["DATABASE_URL"] != f"postgresql+psycopg://dove:{password}@db/dove":
            raise ValueError("database and application credentials do not match")
        if worker["environment"] != app_env:
            raise ValueError("API and worker settings differ")
        volumes = config["volumes"]
        if any(volumes[name].get("name") != f"dove_{name}" or volumes[name].get("external") for name in ("postgres", "postgres18", "objects")):
            raise ValueError("unexpected or external volume mapping")
        def volume(service, target, source, readonly=False):
            return any(v.get("type") == "volume" and v.get("target") == target and v.get("source") == source and bool(v.get("read_only")) == readonly for v in service["volumes"])
        if not (volume(db, "/dove/legacy", "postgres", True) and volume(db, "/var/lib/postgresql", "postgres18") and volume(db, "/dove/objects", "objects") and volume(api, "/data/objects", "objects") and volume(worker, "/data/objects", "objects")):
            raise ValueError("database and object-store mounts do not match the default mapping")
        url = urlsplit(app_env["PUBLIC_URL"])
        if url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
            raise ValueError("application URL must be an origin")
        if mode == "local":
            if (app_env["ENVIRONMENT"], app_env["MODEL_ADAPTER"], app_env["EMAIL_ADAPTER"]) != ("local", "fixture", "local"):
                raise ValueError("local initialization requires local fixture adapters")
            ports = api["ports"]
            if len(ports) != 1 or ports[0].get("host_ip") != "127.0.0.1" or url.scheme != "http" or url.hostname != "127.0.0.1" or (url.port or 80) != int(ports[0]["published"]):
                raise ValueError("local application URL and loopback port do not match")
            if len(db["ports"]) != 1 or db["ports"][0].get("host_ip") != "127.0.0.1":
                raise ValueError("local database must bind loopback only")
        else:
            domain = services["caddy"]["environment"]["DOVE_DOMAIN"]
            if db.get("ports") or api.get("ports") or url.scheme != "https" or not domain or url.hostname != domain or (url.port not in (None, 443)):
                raise ValueError("production URL, domain or private ports are inconsistent")
            if (app_env["ENVIRONMENT"], app_env["MODEL_ADAPTER"], app_env["EMAIL_ADAPTER"]) != ("production", "openai", "resend"):
                raise ValueError("production settings and adapters are incomplete")
            if len(app_env.get("SECRET_KEY", "")) < 40 or app_env["SECRET_KEY"].startswith("local-") or not all(app_env.get(key) for key in ("OPENAI_API_KEY", "RESEND_API_KEY", "RESEND_WEBHOOK_SECRET", "EMAIL_FROM", "REPLY_DOMAIN")) or app_env["EMAIL_FROM"] == "Dove <dove@example.test>" or app_env["REPLY_DOMAIN"] == "reply.example.test":
                raise ValueError("production secrets or provider settings are incomplete")
    except (KeyError, TypeError, ValueError):
        raise SystemExit("Resolved Compose configuration failed safety validation; review mappings, origins and credentials without printing secrets.") from None


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("local", "production"):
        raise SystemExit("Choose exactly local or production.")
    if Path.cwd().resolve() != Path(__file__).resolve().parents[1]:
        raise SystemExit("Run this command from the repository root.")
    if automatic_override_present():
        raise SystemExit("Automatic Compose overrides require a separately reviewed procedure.")
    for key in os.environ:
        local_override = sys.argv[1] == "local" and bool(re.match(r"^(POSTGRES_PASSWORD|DOVE_.*|ENVIRONMENT|PUBLIC_URL|MODEL_ADAPTER|EMAIL_ADAPTER|SECRET_KEY|OPENAI_.*|RESEND_.*|EMAIL_FROM|REPLY_DOMAIN)$", key, re.I))
        if forbidden_selector(key) or local_override:
            raise SystemExit(f"Unset {key} and identify the intended Docker host and project first.")
    dotenv = Path(".env")
    if dotenv.exists():
        selector = unsafe_dotenv_selector(dotenv.read_text(encoding="utf-8-sig"))
        if selector:
            raise SystemExit(f"Remove {selector} from .env and identify the intended host and project first.")
    host = json.loads(docker(["context", "inspect", "--format", "{{json .Endpoints.docker.Host}}"], capture=True))
    if not isinstance(host, str) or not re.match(r"^(unix://|npipe://)", host, re.I):
        raise SystemExit("A local Docker context is required; use a reviewed procedure for other hosts.")
    base = ["compose", "-p", "dove", "-f", "compose.yaml"]
    if sys.argv[1] == "production":
        base += ["-f", "compose.production.yaml"]
    validate_config(json.loads(docker([*base, "config", "--format", "json"], capture=True)), sys.argv[1])
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
