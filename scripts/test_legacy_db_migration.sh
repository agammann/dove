#!/usr/bin/env bash
# Exercise credential rotation against a disposable retained PostgreSQL volume.
set -euo pipefail

project="dove-ci-$(python3 -c 'import secrets; print(secrets.token_hex(12))')"
tmpdir=$(mktemp -d)
override="$tmpdir/compose.override.yaml"
cat > "$override" <<'YAML'
services:
  db:
    ports: !reset []
  api:
    ports: !reset []
YAML
old=local-dove-password
new=ci-new-password-for-retained-volume-2026
old_compose() { POSTGRES_PASSWORD="$old" docker compose -f compose.yaml -f "$override" -p "$project" "$@"; }
new_compose() { POSTGRES_PASSWORD="$new" docker compose -f compose.yaml -f "$override" -p "$project" "$@"; }
if docker volume inspect "${project}_postgres" >/dev/null 2>&1 || docker network inspect "${project}_default" >/dev/null 2>&1; then
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
printf "ALTER ROLE dove PASSWORD :'new_password';\n" | \
  new_compose exec -T db psql -U dove -d dove -v ON_ERROR_STOP=1 -v new_password="$new"

db_client() {
  local password="$1"
  shift
  docker run --rm --network "${project}_default" -e "PGPASSWORD=$password" postgres:17.6-alpine \
    psql -h db -U dove -d dove -v ON_ERROR_STOP=1 "$@"
}
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

