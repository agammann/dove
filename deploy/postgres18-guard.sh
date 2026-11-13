#!/bin/sh
set -eu

# This checks only these Compose mounts; other projects, hosts and storage
# require an operator inventory before using the fresh-install override.
mode=${1:?Expected start or initialize}
shift
legacy=/dove/legacy
objects=/dove/objects
target=/var/lib/postgresql
cluster=$target/18/docker
attempt=$target/.dove-init-attempt
binding=$objects/.dove-pg18-binding
marker=$cluster/.dove-init-complete
fail() { echo "Dove PostgreSQL 18: $*" >&2; exit 1; }
[ "${PGDATA:-}" = "$cluster" ] || fail 'unexpected PGDATA; use a reviewed custom procedure'
[ -d "$legacy" ] && [ -d "$target" ] && [ -d "$objects" ] || fail 'required storage mount is missing'
legacy_entries=$(ls -A "$legacy") || fail 'could not inspect legacy storage'
[ -z "$legacy_entries" ] || fail 'legacy PostgreSQL storage is populated; preserve it and use a reviewed migration'

case "$mode" in
  initialize)
    [ "${DOVE_PG18_FRESH_INSTALL:-}" = 'confirmed-no-existing-dove-data' ] || fail 'fresh-install confirmation required'
    target_entries=$(ls -A "$target") || fail 'could not inspect PostgreSQL 18 storage'
    object_entries=$(ls -A "$objects") || fail 'could not inspect object storage'
    [ -z "$target_entries" ] && [ -z "$object_entries" ] || fail 'target or object storage is not empty; preserve it for review'
    # Both permanent claims fail closed after interruption or competition.
    mkdir "$attempt" || fail 'another initialization has already claimed this database target'
    target_entries=$(ls -A "$target") || fail 'could not recheck database target'
    object_entries=$(ls -A "$objects") || fail 'could not recheck object storage'
    [ "$target_entries" = '.dove-init-attempt' ] && [ -z "$object_entries" ] || fail 'storage changed during initialization'
    mkdir "$binding" || fail 'another initialization has already claimed this object store'
    token=$(cat /proc/sys/kernel/random/uuid) || fail 'could not create binding identity'
    case "$token" in ''|*[!0-9a-f-]*) fail 'invalid binding identity' ;; esac
    [ "${#token}" -eq 36 ] || fail 'invalid binding identity'
    printf '%s\n' "$token" > "$attempt/object-id"
    printf '%s\n' "$token" > "$binding/object-id"
    # The API and worker run as UID 10001. Only an inspected empty object
    # volume is assigned to that UID; pre-existing object data is never changed.
    chown 10001:10001 "$objects"
    sync "$attempt/object-id" "$binding/object-id" "$attempt" "$binding" "$objects" "$target"
    ;;
  start)
    [ -d "$attempt" ] && [ ! -L "$attempt" ] && [ -d "$binding" ] && [ ! -L "$binding" ] || fail 'initialization record or object binding is missing'
    [ -f "$attempt/object-id" ] && [ ! -L "$attempt/object-id" ] && [ -f "$binding/object-id" ] && [ ! -L "$binding/object-id" ] || fail 'object binding is invalid'
    token=$(cat "$attempt/object-id")
    case "$token" in ''|*[!0-9a-f-]*) fail 'object binding is invalid' ;; esac
    [ "${#token}" -eq 36 ] && [ "$(cat "$binding/object-id")" = "$token" ] || fail 'database and object storage bindings differ'
    [ -d "$target/18" ] && [ ! -L "$target/18" ] && [ -d "$cluster" ] && [ ! -L "$cluster" ] || fail 'PG18 cluster is missing or invalid'
    [ -f "$cluster/PG_VERSION" ] && [ ! -L "$cluster/PG_VERSION" ] && [ "$(cat "$cluster/PG_VERSION")" = 18 ] || fail 'target is not a PostgreSQL 18 cluster'
    [ -f "$marker" ] && [ ! -L "$marker" ] || fail 'initialization marker is missing; preserve the incomplete target'
    control=$(pg_controldata "$cluster") || fail 'could not read cluster identity'
    identity=$(printf '%s\n' "$control" | sed -n 's/^Database system identifier:[[:space:]]*//p')
    case "$identity" in ''|*[!0-9]*) fail 'cluster identity is invalid' ;; esac
    [ "$(cat "$marker")" = "dove-postgres18-complete-v1:$identity:$token" ] || fail 'initialization marker does not match this cluster and object store'
    ;;
  *) fail 'unknown startup mode' ;;
esac
exec /usr/local/bin/docker-entrypoint.sh "$@"
