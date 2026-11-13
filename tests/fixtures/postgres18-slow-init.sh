#!/bin/sh
set -eu
touch "$PGDATA/.synthetic-slow-init-started"
# Even a premature marker must not make the temporary Unix-socket server healthy.
printf 'synthetic-premature-marker\n' > "$PGDATA/.dove-init-complete"
sleep 12
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE TABLE slow_fixture(value text); INSERT INTO slow_fixture VALUES ('completed');"
touch "$PGDATA/.synthetic-slow-init-finished"
