"""Exercise only uniquely named, synthetic Docker resources; never inspect a real stack."""

import json
import hashlib
import io
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import time
import uuid

prefix = "dovepg18test" + uuid.uuid4().hex
env = {k: v for k, v in os.environ.items() if not re.match(r"^(COMPOSE_|DOCKER_HOST$|DOCKER_CONTEXT$|POSTGRES_PASSWORD$|DOVE_DOMAIN$|DOVE_PG18_FRESH_INSTALL$)", k, re.I)}
env.update(POSTGRES_PASSWORD="synthetic-only-password", DOVE_DOMAIN="fixture.invalid", DOVE_PG18_FRESH_INSTALL="confirmed-no-existing-dove-data")
root = Path(__file__).resolve().parents[1]
fixture = Path(tempfile.mkdtemp(prefix="dove-pg18-guard-"))
override = fixture / "no-ports.yaml"
override.write_text('services:\n  db:\n    ports: !override []\n    network_mode: none\nnetworks:\n  default: !override {external: true, name: none}\n', encoding="utf-8")
projects = []
containers = []


def docker(*args, check=True, input_text=None):
    result = subprocess.run(["docker", *args], cwd=root, env=env, input=input_text, capture_output=True, text=True, timeout=180)
    if check and result.returncode:
        raise AssertionError(f"Docker fixture failed: {args[:4]}: {result.stderr}")
    return result


def compose(project, *args, initialize=False, production=False):
    files = ["-f", "compose.yaml"]
    if production:
        files += ["-f", "compose.production.yaml"]
    if initialize:
        files += ["-f", "compose.postgres18-init.yaml"]
    return docker("compose", "-p", project, *files, "-f", str(override), *args, check=False)


def fresh_project(label):
    project = prefix + label
    for suffix in ("postgres", "postgres18", "objects"):
        assert docker("volume", "inspect", f"{project}_{suffix}", check=False).returncode != 0
    assert docker("network", "inspect", f"{project}_default", check=False).returncode != 0
    projects.append(project)
    return project


def require_ok(result):
    assert result.returncode == 0, result.stderr


def rejected(result, text):
    assert result.returncode != 0 and text in (result.stdout + result.stderr), result.stderr


def mutate(volume, script):
    return docker("run", "--rm", "--network", "none", "--entrypoint", "sh", "-v", f"{volume}:/fixture", "postgres:18.4-alpine", "-c", script)


def start(project, *, production=False):
    require_ok(compose(project, "up", "-d", "--wait", "--wait-timeout", "180", "db", initialize=True, production=production))
    require_ok(compose(project, "up", "-d", "--force-recreate", "--wait", "--wait-timeout", "180", "db", production=production))


host = json.loads(docker("context", "inspect", "--format", "{{json .Endpoints.docker.Host}}").stdout)
assert re.match(r"^(unix://|npipe://)", host, re.I), "Only a local Docker context is supported"
try:
    local = fresh_project("local")
    rejected(compose(local, "run", "--no-deps", "db", "postgres", "--help"), "initialization record")
    rejected(compose(local, "run", "--no-deps", "-e", "PGDATA=/tmp/unreviewed", "db", "postgres", "--help"), "unexpected PGDATA")
    rejected(compose(local, "run", "--no-deps", "-e", "DOVE_PG18_FRESH_INSTALL=invalid", "db", "postgres", "--help", initialize=True), "fresh-install confirmation required")
    start(local)
    digest = hashlib.sha256(b"synthetic-document").hexdigest()
    require_ok(compose(local, "exec", "-T", "db", "psql", "-U", "dove", "-d", "dove", "-v", "ON_ERROR_STOP=1", "-c", f"CREATE TABLE fixture_objects (path text, sha256 text); INSERT INTO fixture_objects VALUES ('org/document.txt', '{digest}'); CREATE ROLE fixture_reader LOGIN;"))
    require_ok(compose(local, "exec", "-T", "db", "createdb", "-U", "dove", "fixture_second_database"))
    require_ok(compose(local, "exec", "-T", "db", "psql", "-U", "dove", "-d", "fixture_second_database", "-v", "ON_ERROR_STOP=1", "-c", "CREATE TABLE fixture_extra(value text); INSERT INTO fixture_extra VALUES ('second-database');"))
    mutate(f"{local}_objects", "mkdir -p /fixture/org; printf synthetic-document > /fixture/org/document.txt; chown -R 10001:10001 /fixture/org")
    require_ok(compose(local, "stop", "db"))
    require_ok(compose(local, "up", "-d", "--wait", "--wait-timeout", "180", "db"))
    query = compose(local, "exec", "-T", "db", "psql", "-U", "dove", "-d", "dove", "-Atc", "SELECT path FROM fixture_objects")
    require_ok(query)
    assert query.stdout.strip() == "org/document.txt"
    mutate(f"{local}_objects", "test \"$(cat /fixture/org/document.txt)\" = synthetic-document; test \"$(stat -c %u /fixture)\" = 10001")
    role = compose(local, "exec", "-T", "db", "psql", "-U", "dove", "-d", "dove", "-Atc", "SELECT rolname FROM pg_roles WHERE rolname = 'fixture_reader'")
    require_ok(role)
    assert role.stdout.strip() == "fixture_reader"
    other = compose(local, "exec", "-T", "db", "psql", "-U", "dove", "-d", "fixture_second_database", "-Atc", "SELECT value FROM fixture_extra")
    require_ok(other)
    assert other.stdout.strip() == "second-database"

    # Restore a quiescent synthetic database dump and its paired object into a
    # different fresh cluster. Do not overwrite the new cluster's binding.
    source_id = compose(local, "ps", "-q", "db").stdout.strip()
    dump = subprocess.run(["docker", "exec", source_id, "pg_dump", "-U", "dove", "-d", "dove", "-Fc"], cwd=root, env=env, capture_output=True, timeout=120, check=True).stdout
    archive = subprocess.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "tar", "-v", f"{local}_objects:/fixture:ro", "postgres:18.4-alpine", "-C", "/fixture", "-cf", "-", "."], cwd=root, env=env, capture_output=True, timeout=120, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        object_bytes = tar.extractfile("./org/document.txt").read()
    assert hashlib.sha256(object_bytes).hexdigest() == digest
    restored = fresh_project("restore")
    start(restored)
    target_id = compose(restored, "ps", "-q", "db").stdout.strip()
    subprocess.run(["docker", "exec", "-i", target_id, "pg_restore", "--exit-on-error", "--no-owner", "-U", "dove", "-d", "dove"], cwd=root, env=env, input=dump, capture_output=True, timeout=120, check=True)
    subprocess.run(["docker", "run", "--rm", "-i", "--network", "none", "--entrypoint", "sh", "-v", f"{restored}_objects:/fixture", "postgres:18.4-alpine", "-c", "mkdir -p /fixture/org; cat > /fixture/org/document.txt; chown -R 10001:10001 /fixture/org"], cwd=root, env=env, input=object_bytes, capture_output=True, timeout=120, check=True)
    row = compose(restored, "exec", "-T", "db", "psql", "-U", "dove", "-d", "dove", "-Atc", "SELECT path || ':' || sha256 FROM fixture_objects")
    require_ok(row)
    assert row.stdout.strip() == f"org/document.txt:{digest}"
    require_ok(compose(restored, "stop", "db"))
    require_ok(compose(restored, "up", "-d", "--wait", "--wait-timeout", "180", "db"))
    mutate(f"{restored}_objects", "test \"$(cat /fixture/org/document.txt)\" = synthetic-document")
    require_ok(compose(restored, "stop", "db"))
    print("PASS: paired synthetic database/object backup restored to a separate bound cluster")
    require_ok(compose(local, "stop", "db"))
    mutate(f"{local}_postgres18", "mv /fixture/18/docker/.dove-init-complete /fixture/18/docker/.saved-marker")
    rejected(compose(local, "run", "--no-deps", "db", "postgres", "--help"), "initialization marker is missing")
    mutate(f"{local}_postgres18", "printf 'incorrect-marker\\n' > /fixture/18/docker/.dove-init-complete")
    rejected(compose(local, "run", "--no-deps", "db", "postgres", "--help"), "initialization marker does not match")
    mutate(f"{local}_postgres18", "mv -f /fixture/18/docker/.saved-marker /fixture/18/docker/.dove-init-complete")
    mutate(f"{local}_objects", "mv /fixture/.dove-pg18-binding/object-id /fixture/.dove-pg18-binding/object-id.saved; printf '00000000-0000-0000-0000-000000000000\\n' > /fixture/.dove-pg18-binding/object-id")
    rejected(compose(local, "run", "--no-deps", "db", "postgres", "--help"), "bindings differ")
    mutate(f"{local}_objects", "mv /fixture/.dove-pg18-binding/object-id.saved /fixture/.dove-pg18-binding/object-id")
    require_ok(compose(local, "up", "-d", "--wait", "--wait-timeout", "180", "db"))
    require_ok(compose(local, "stop", "db"))
    print("PASS: fresh initialization, paired object binding, roles/databases and restart")

    legacy = fresh_project("legacy")
    old_name = f"{legacy}pg17"
    old = docker("run", "-d", "--name", old_name, "--network", "none", "-e", "POSTGRES_USER=dove", "-e", "POSTGRES_DB=dove", "-e", "POSTGRES_PASSWORD=synthetic-only-password", "-v", f"{legacy}_postgres:/var/lib/postgresql/data", "postgres:17.6-alpine").stdout.strip()
    assert re.fullmatch(r"[a-f0-9]{64}", old)
    containers.append(old)
    for _ in range(90):
        if docker("exec", old, "pg_isready", "-h", "127.0.0.1", "-U", "dove", "-d", "dove", check=False).returncode == 0:
            break
        time.sleep(1)
    else:
        raise AssertionError("Synthetic PostgreSQL 17 fixture did not become ready")
    docker("exec", old, "psql", "-U", "dove", "-d", "dove", "-v", "ON_ERROR_STOP=1", "-c", "CREATE TABLE old_fixture(value text); INSERT INTO old_fixture VALUES ('preserved-legacy');")
    docker("stop", old)
    rejected(compose(legacy, "run", "--no-deps", "db", "postgres", "--help", initialize=True), "legacy PostgreSQL storage is populated")
    docker("start", old)
    for _ in range(90):
        if docker("exec", old, "pg_isready", "-h", "127.0.0.1", "-U", "dove", "-d", "dove", check=False).returncode == 0:
            break
        time.sleep(1)
    else:
        raise AssertionError("Synthetic PostgreSQL 17 fixture did not restart")
    assert docker("exec", old, "psql", "-U", "dove", "-d", "dove", "-Atc", "SELECT value FROM old_fixture").stdout.strip() == "preserved-legacy"
    docker("stop", old)
    objects = fresh_project("objects")
    mutate(f"{objects}_objects", "printf preserved-object > /fixture/sentinel")
    rejected(compose(objects, "run", "--no-deps", "db", "postgres", "--help", initialize=True), "target or object storage is not empty")
    mutate(f"{objects}_objects", "test \"$(cat /fixture/sentinel)\" = preserved-object")
    target_filled = fresh_project("targetfilled")
    mutate(f"{target_filled}_postgres18", "printf preserved-target > /fixture/sentinel")
    rejected(compose(target_filled, "run", "--no-deps", "db", "postgres", "--help", initialize=True), "target or object storage is not empty")
    mutate(f"{target_filled}_postgres18", "test \"$(cat /fixture/sentinel)\" = preserved-target")
    print("PASS: existing legacy database and object storage are preserved and block initialization")

    incomplete = fresh_project("incomplete")
    guard = root / "deploy" / "postgres18-guard.sh"
    ready = root / "deploy" / "postgres18-ready.sh"
    failing = root / "tests" / "fixtures" / "postgres18-init-fail.sh"
    isolated = ["run", "--network", "none", "--entrypoint", "sh", "-e", "POSTGRES_PASSWORD=synthetic-only-password", "-e", "DOVE_PG18_FRESH_INSTALL=confirmed-no-existing-dove-data", "-v", f"{incomplete}_postgres:/dove/legacy:ro", "-v", f"{incomplete}_postgres18:/var/lib/postgresql", "-v", f"{incomplete}_objects:/dove/objects", "-v", f"{guard}:/dove/guard.sh:ro", "-v", f"{failing}:/docker-entrypoint-initdb.d/yy-synthetic-failure.sh:ro", "-v", f"{ready}:/docker-entrypoint-initdb.d/zz-dove-ready.sh:ro", "postgres:18.4-alpine", "/dove/guard.sh"]
    rejected(docker(*isolated, "initialize", "postgres", check=False), "synthetic initialization failure")
    rejected(compose(incomplete, "run", "--no-deps", "db", "postgres", "--help", initialize=True), "target or object storage is not empty")
    rejected(compose(incomplete, "run", "--no-deps", "db", "postgres", "--help"), "initialization marker is missing")
    print("PASS: prior/incomplete initialization cannot be restarted as fresh")

    unreadable = fresh_project("unreadable")
    ls_fail = root / "tests" / "fixtures" / "postgres18-ls-fail.sh"
    fail_args = ["run", "--network", "none", "--entrypoint", "sh", "-e", "PATH=/test-bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "-v", f"{unreadable}_postgres:/dove/legacy:ro", "-v", f"{unreadable}_postgres18:/var/lib/postgresql", "-v", f"{unreadable}_objects:/dove/objects", "-v", f"{guard}:/dove/guard.sh:ro", "-v", f"{ls_fail}:/test-bin/ls:ro", "postgres:18.4-alpine", "/dove/guard.sh", "start", "postgres", "--help"]
    rejected(docker(*fail_args, check=False), "could not inspect legacy storage")
    print("PASS: failed legacy inspection blocks startup")

    race = fresh_project("race")
    for suffix in ("postgres", "postgres18", "objects"):
        require_ok(docker("volume", "create", f"{race}_{suffix}"))
    race_args = ["docker", "run", "--network", "none", "--entrypoint", "sh", "-e", "DOVE_PG18_FRESH_INSTALL=confirmed-no-existing-dove-data", "-v", f"{race}_postgres:/dove/legacy:ro", "-v", f"{race}_postgres18:/var/lib/postgresql", "-v", f"{race}_objects:/dove/objects", "-v", f"{guard}:/dove/guard.sh:ro", "postgres:18.4-alpine", "/dove/guard.sh", "initialize", "postgres", "--help"]
    processes = [subprocess.Popen(race_args, cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for _ in range(2)]
    assert sum(p.wait(timeout=120) == 0 for p in processes) == 1
    rejected(compose(race, "run", "--no-deps", "db", "postgres", "--help"), "PG18 cluster is missing")
    print("PASS: simultaneous initializers cannot both claim the target")

    slow = fresh_project("slow")
    slow_override = fixture / "slow.yaml"
    slow_script = root / "tests" / "fixtures" / "postgres18-slow-init.sh"
    slow_override.write_text("services:\n  db:\n    volumes:\n      - " + json.dumps(f"{slow_script}:/docker-entrypoint-initdb.d/yy-slow.sh:ro") + "\n", encoding="utf-8")
    require_ok(compose(slow, "-f", str(slow_override), "up", "-d", "db", initialize=True))
    result = compose(slow, "-f", str(slow_override), "ps", "-q", "db", initialize=True)
    require_ok(result)
    slow_id = result.stdout.strip()
    assert re.fullmatch(r"[a-f0-9]{64}", slow_id)
    containers.append(slow_id)
    for _ in range(60):
        if docker("exec", slow_id, "test", "-f", "/var/lib/postgresql/18/docker/.synthetic-slow-init-started", check=False).returncode == 0:
            break
        time.sleep(0.5)
    else:
        raise AssertionError("Slow synthetic init did not start")
    observed = False
    for _ in range(11):
        if docker("exec", slow_id, "test", "-f", "/var/lib/postgresql/18/docker/.synthetic-slow-init-finished", check=False).returncode == 0:
            break
        health = json.loads(docker("inspect", "--format", "{{json .State.Health}}", slow_id).stdout)
        assert health["Status"] != "healthy", "Temporary server was reported healthy"
        observed |= bool(health["Log"])
        time.sleep(1)
    assert observed, "No real healthcheck occurred during slow initialization"
    require_ok(compose(slow, "-f", str(slow_override), "up", "-d", "--wait", "--wait-timeout", "180", "db", initialize=True))
    require_ok(compose(slow, "up", "-d", "--force-recreate", "--wait", "--wait-timeout", "180", "db"))
    result = compose(slow, "exec", "-T", "db", "psql", "-U", "dove", "-d", "dove", "-Atc", "SELECT value FROM slow_fixture")
    require_ok(result)
    assert result.stdout.strip() == "completed"
    require_ok(compose(slow, "stop", "db"))
    print("PASS: slow initialization remains nonhealthy until final TCP server and survives recreation")

    production = fresh_project("production")
    start(production, production=True)
    require_ok(compose(production, "stop", "db", production=True))
    require_ok(compose(production, "up", "-d", "--wait", "--wait-timeout", "180", "db", production=True))
    require_ok(compose(production, "stop", "db", production=True))
    print("PASS: production overlay uses the same fresh and restart guard")
finally:
    for project in projects:
        compose(project, "stop", "db")
    for container in containers:
        docker("stop", container, check=False)
    print(f"Synthetic fixture projects and volumes retained under {prefix}; temporary override: {fixture}")
