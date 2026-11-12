#!/usr/bin/env bash
# Exercise credential rotation against a disposable retained PostgreSQL volume.
set -euo pipefail

project=dove-legacy-ci
old=local-dove-password
new=ci-new-password-for-retained-volume-2026
old_compose() { POSTGRES_PASSWORD="$old" DOVE_DB_PORT=35429 docker compose -p "$project" "$@"; }
new_compose() { POSTGRES_PASSWORD="$new" DOVE_DB_PORT=35429 docker compose -p "$project" "$@"; }
cleanup() { new_compose down --volumes --remove-orphans; }
trap cleanup EXIT

old_compose up --detach --wait --wait-timeout 180 db
old_compose exec -T db psql -U dove -d dove -v ON_ERROR_STOP=1 -c \
  "CREATE TABLE migration_probe (value text); INSERT INTO migration_probe VALUES ('retained');"
old_compose down
new_compose up --detach --wait --wait-timeout 180 db

# The PostgreSQL image does not rotate a role when its environment changes.
printf "ALTER ROLE dove PASSWORD :'new_password';\n" | \
  new_compose exec -T db psql -U dove -d dove -v ON_ERROR_STOP=1 -v new_password="$new"

if new_compose exec -T -e PGPASSWORD="$old" db psql -h 127.0.0.1 -U dove -d dove -c 'SELECT 1' >/dev/null 2>&1; then
  echo "Old password unexpectedly authenticated after rotation" >&2
  exit 1
fi
value=$(new_compose exec -T -e PGPASSWORD="$new" db psql -h 127.0.0.1 -U dove -d dove -At -v ON_ERROR_STOP=1 -c 'SELECT value FROM migration_probe')
test "$value" = retained
new_compose up --build --detach --wait --wait-timeout 180 api worker
new_compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
new_compose ps --status running --services | grep -qx worker

