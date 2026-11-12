#!/usr/bin/env bash
# Exercise credential rotation against a disposable retained PostgreSQL volume.
set -euo pipefail

project="dove-ci-$(python3 -c 'import secrets; print(secrets.token_hex(12))')"
tmpdir=$(mktemp -d)
override="$tmpdir/compose.override.yaml"
envfile="$tmpdir/empty.env"
: > "$envfile"
cat > "$override" <<'YAML'
services:
  db:
    ports: !reset []
  api:
    ports: !reset []
YAML
old=local-dove-password
new=ci-new-password-for-retained-volume-2026
isolated_docker() { env -i PATH="$PATH" HOME="$tmpdir" POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}" docker "$@"; }
old_compose() { POSTGRES_PASSWORD="$old" isolated_docker compose --env-file "$envfile" -f compose.yaml -f "$override" -p "$project" "$@"; }
new_compose() { POSTGRES_PASSWORD="$new" isolated_docker compose --env-file "$envfile" -f compose.yaml -f "$override" -p "$project" "$@"; }
if isolated_docker volume inspect "${project}_postgres" >/dev/null 2>&1 || isolated_docker network inspect "${project}_default" >/dev/null 2>&1; then
  echo "Generated test project already exists; refusing to use it" >&2
  rm -rf "$tmpdir"
  exit 1
fi
cleanup() { new_compose down --volumes --remove-orphans; rm -rf "$tmpdir"; }
trap cleanup EXIT

old_compose up --detach --wait --wait-timeout 180 db
old_compose exec -T db psql -U dove -d dove -v ON_ERROR_STOP=1 -c \
  "CREATE TABLE migration_probe (value text); INSERT INTO migration_probe VALUES ('retained');"
old_compose down
new_compose up --detach --wait --wait-timeout 180 db

# The PostgreSQL image does not rotate a role when its environment changes.
db_client() {
  local password="$1"
  shift
  isolated_docker run --rm --network "${project}_default" -e "PGPASSWORD=$password" postgres:17.6-alpine \
    psql -h db -U dove -d dove -v ON_ERROR_STOP=1 "$@"
}
db_client "$old" -c 'SELECT 1' >/dev/null
if db_client "$new" -c 'SELECT 1' >/dev/null 2>&1; then
  echo "New password unexpectedly authenticated before rotation" >&2
  exit 1
fi

# Drive the documented interactive password command in a disposable TTY.
POSTGRES_PASSWORD="$new" DOVE_TEST_COMPOSE_PROJECT="$project" \
  DOVE_TEST_COMPOSE_OVERRIDE="$override" DOVE_TEST_DOCKER_HOME="$tmpdir" python3 - <<'PY_PSQL_TEST'
#!/usr/bin/env python3
"""Drive the documented psql password prompt in a disposable Compose project."""

import os
import pty
import select
import signal
import sys
import termios
import time


def main():
    project = os.environ["DOVE_TEST_COMPOSE_PROJECT"]
    override = os.environ["DOVE_TEST_COMPOSE_OVERRIDE"]
    password = os.environ["POSTGRES_PASSWORD"].encode()
    if not password or b"\n" in password or b"\r" in password:
        raise ValueError("Expected a single-line synthetic password")

    pid, fd = pty.fork()
    if pid == 0:
        settings = termios.tcgetattr(0)
        settings[3] &= ~termios.ECHO
        termios.tcsetattr(0, termios.TCSANOW, settings)
        env = {"PATH": os.environ["PATH"], "HOME": os.environ["DOVE_TEST_DOCKER_HOME"],
               "POSTGRES_PASSWORD": password.decode(), "LC_ALL": "C", "TERM": "dumb"}
        os.execvpe(
            "docker",
            ["docker", "compose", "--env-file", os.path.join(env["HOME"], "empty.env"),
             "-f", "compose.yaml", "-f", override,
             "-p", project, "exec", "-e", "LC_ALL=C", "db", "psql", "-U", "dove", "-d", "dove"],
            env,
        )

    buffer = b""
    deadline = time.monotonic() + 90
    waited = False

    def expect(token):
        nonlocal buffer
        while token not in buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                raise RuntimeError("Timed out waiting for the psql prompt")
            try:
                chunk = os.read(fd, 4096)
            except OSError as exc:
                raise RuntimeError("psql closed before the expected prompt") from exc
            if not chunk:
                raise RuntimeError("psql closed before the expected prompt")
            buffer += chunk
            if len(buffer) > 65536:
                raise RuntimeError("Unexpectedly large psql output")
        buffer = buffer.split(token, 1)[1]

    try:
        expect(b"dove=# ")
        os.write(fd, b"\\password dove\n")
        expect(b'Enter new password for user "dove": ')
        os.write(fd, password + b"\n")
        expect(b"Enter it again: ")
        os.write(fd, password + b"\n")
        expect(b"dove=# ")
        os.write(fd, b"\\q\n")
        while True:
            result, status = os.waitpid(pid, os.WNOHANG)
            if result:
                waited = True
                if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                    raise RuntimeError("Interactive psql exited unsuccessfully")
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Timed out waiting for psql to exit")
            time.sleep(0.1)
    finally:
        if not waited:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        os.close(fd)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError) as error:
        print(f"Interactive password rotation test failed: {error}", file=sys.stderr)
        sys.exit(1)
PY_PSQL_TEST

if db_client "$old" -c 'SELECT 1' >/dev/null 2>&1; then
  echo "Old password unexpectedly authenticated after rotation" >&2
  exit 1
fi
value=$(db_client "$new" -At -c 'SELECT value FROM migration_probe')
test "$value" = retained
new_compose up --build --detach --wait --wait-timeout 180 api worker
new_compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
new_compose ps --status running --services | grep -qx worker
new_compose exec -T worker python -c 'import os; from sqlalchemy import create_engine, text; engine = create_engine(os.environ["DATABASE_URL"]); conn = engine.connect(); assert conn.execute(text("SELECT 1")).scalar_one() == 1; conn.close(); engine.dispose()'


