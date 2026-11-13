#!/bin/sh
set -eu
[ "${PGDATA:-}" = /var/lib/postgresql/18/docker ]
[ "$(cat "$PGDATA/PG_VERSION")" = 18 ]
token=$(cat /var/lib/postgresql/.dove-init-attempt/object-id)
[ "$(cat /dove/objects/.dove-pg18-binding/object-id)" = "$token" ]
control=$(pg_controldata "$PGDATA")
identity=$(printf '%s\n' "$control" | sed -n 's/^Database system identifier:[[:space:]]*//p')
case "$identity" in ''|*[!0-9]*) exit 1 ;; esac
printf 'dove-postgres18-complete-v1:%s:%s\n' "$identity" "$token" > "$PGDATA/.dove-init-complete"
sync "$PGDATA/.dove-init-complete" "$PGDATA"
