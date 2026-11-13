# First run

[Back to Dove](../README.md) Â· [Documentation](README.md)

Use fictional documents in local mode. Analysis and email are simulated; the public website is a separate service.

## Prerequisites

Install Git, Python 3.12 or newer, and Docker with its Linux container engine. Start Docker, then confirm `docker version` shows a server and `docker compose version` succeeds. Use a current Compose plugin supporting `--wait`. Docker supplies Node and pnpm.

```sh
git clone https://github.com/agammann/dove.git
cd dove
```

Run all following commands beside `compose.yaml`.

## Create local configuration

Before the first Compose command, generate an ignored `.env` with a unique database password. On Linux or in a POSIX shell, run:

```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/workspace" -w /workspace python:3.12.11-slim python scripts/setup_env.py
```

In Windows PowerShell, run:

```powershell
docker run --rm --mount "type=bind,source=$((Get-Location).Path),target=/workspace" --workdir /workspace python:3.12.11-slim python scripts/setup_env.py
```

The setup command preserves an existing `.env`. If one already exists, ensure it contains a unique `POSTGRES_PASSWORD` of at least 24 URL-safe characters. Keep the file private; never commit it. A blank or missing password stops Compose configuration.

## Choose a local address

The default app address is `http://127.0.0.1:8000`; PostgreSQL uses loopback port 54329. If app port 8000 is occupied, edit the generated `.env` and change both lines before startup:

```dotenv
DOVE_PORT=8010
PUBLIC_URL=http://127.0.0.1:8010
```

If Windows reserves the PostgreSQL host port or another service uses it, set `DOVE_DB_PORT` to an available loopback port in that `.env`, for example `DOVE_DB_PORT=55429`. You do not need to edit Compose or change `DATABASE_URL`: containers still connect to `db:5432`.

Keep `ENVIRONMENT=local`, `MODEL_ADAPTER=fixture`, and `EMAIL_ADAPTER=local`. Review an existing `.env` before editing it. Always open exactly `PUBLIC_URL`: `localhost` and `127.0.0.1` are different origins.

## Initialize a fresh database

These instructions apply to this checkout; the published v1.0.0 archive uses PostgreSQL 17. Before initializing, inventory all previous Dove databases, additional databases and roles, object storage, Docker hosts, Compose project names, volume or bind-mount mappings, overrides and backups. The guard can inspect only the selected project's `postgres` and `objects` mounts. It cannot discover other projects, external volumes, bind mounts, remote databases or other hosts. Stop every potential writer and storage change during the inspection and initialization. If any existing Dove data may be present, preserve its original source, mapping and backups and plan a separately reviewed migration; a fresh database is not a migration.

Only after confirming no Dove data exists, run this from the repository root and type the exact requested phrase:

```sh
python scripts/confirm_postgres18_fresh.py local
```

Use a clean shell for initialization: the helper rejects inherited Compose/Docker selectors, `DATABASE_URL`, `PG*`, `POSTGRES_PASSWORD` and Dove/application settings that could override the generated `.env`. It also rejects selectors such as `COMPOSE_FILE`, `PGDATA` and `DATABASE_URL` inside `.env`, and automatic `compose.override.*`/`docker-compose.override.*` files; keep its intended password and local settings in `.env`. It validates the resolved default volume mappings, URL-safe database password, matching API/worker credentials, loopback ports and local fixture settings without displaying secrets. Docker Compose otherwise gives shell variables precedence and can load overrides automatically, so keep selectors and override files absent and use the same reviewed configuration for later startup and backup commands.

The helper checks for existing project containers; the guard requires empty legacy PostgreSQL, new PostgreSQL and object volumes. It writes a permanent attempt record and binds the new cluster and object volume. Normal startup checks both identities. Those markers detect mismatched volumes; they do not prove a backup is complete or detect external storage. If initialization is interrupted, preserve all volumes and inspect the logs and mappings; do not reset a volume, forge a marker or retry fresh initialization. If initialization completed before the helper switched to normal startup, `docker compose up --detach --wait db` checks the binding. Other failures require an installation-specific recovery.

## Start and check health

```sh
docker compose up --build --detach --wait --wait-timeout 180
docker compose ps
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read().decode())"
```

The API applies migrations automatically. Wait for successful startup before continuing. PostgreSQL and the API should be healthy; the worker should be running. Expected health response: `{"status":"ok","version":"0.1.0"}`. That check runs inside the container, whose port stays 8000 even when the browser uses 8010. It does not verify the worker or external providers.

```sh
docker compose exec api python -m dove.cli seed
```

Expected output starts `Sample accounts ready`. Repeating `seed` keeps existing sample work; it refuses live adapters or production mode. Open the configured browser address.

| Sample | Email |
| :--- | :--- |
| Design studio | studio@dove.example |
| Consulting firm | consulting@dove.example |
| IT provider | it@dove.example |

The shared fictional sample password is `Dove-local-sample-2026!`. It is only for local samples.

## Walkthrough

1. Choose **Design studio** to fill the sample credentials, click **Sign in**, then open **Brand identity handoff**.
2. Review source evidence. Satisfy acceptance, deliverables, agreed amount and billing recipient with explanations; leave the purchase order missing.
3. Confirm the checklist. Review or edit a request, select the authorized contact, grant follow up permission, then authorize it.
4. In **Resolve**, inspect simulated provider acceptance. Use **Local inbox** to submit the supplied fictional purchase order reply.
5. Wait for the worker, review its decision and satisfy the purchase order requirement using the incoming evidence.
6. In **Package**, generate the confirmed USD 2400.00 invoice line or attach an invoice PDF. Enter dates, summary and recipients; approve supporting documents for delivery.
7. Preview the invoice and manifest, download the ZIP, approve the exact package, then separately authorize delivery.

Local completion means simulated provider acceptance, not real email delivery or payment. The consulting example has conflicting amounts; the IT example lacks acceptance and a completion checklist.

## Stop and resume

`docker compose down` stops the stack and retains database/object volumes. Resume with the startup command. Do not add `--volumes` if retaining data.

If you used an older PostgreSQL 17 sample volume with the former shared password, preserve its actual checkout and matching Compose mapping until a separately reviewed migration. First back up any work and matching object data you need to retain. The last pre-PG18 checkout (`ebc675ca42bdeb55b55648dd79ecd5db2c517b2a`) includes the configuration helper and the tested rotation procedure; the published v1.0.0 archive does not include that helper. Do not silently substitute a different checkout or assume those commands exist: use a reviewed procedure for the installed version and its actual mappings. Changing an environment value alone does not change a password already stored in a PostgreSQL volume. Do not remove the volume to rotate credentials.

To deliberately delete and recreate only the three fictional sample workspaces, use `docker compose exec api python -m dove.cli reset-samples`. It refuses production mode and non-sample organizations. This is not a networking repair command.

## Troubleshooting

| Symptom | Action |
| :--- | :--- |
| Docker daemon unavailable | Start Docker and confirm the Linux engine. |
| Unknown `--wait` option | Update Docker Compose. |
| Port 8000 occupied | Set both alternate port values above, then rerun startup. |
| PostgreSQL host port occupied or access forbidden | Set `DOVE_DB_PORT` to an available port in `.env`, then rerun startup. The binding remains loopback only; container port 5432 stays unchanged. |
| Writes return 403 | Match the browser address exactly to `PUBLIC_URL`, then restart after environment changes. |
| API unhealthy | Inspect `docker compose logs --tail=80 api db` before seeding. |
| Pending work | Check worker logs and work/organization pause settings. |

If PostgreSQL is healthy but the API reports `failed to resolve host 'db'` after a Docker interruption, recreate only the app containers, preserving volumes:

```sh
docker compose up --detach --force-recreate --wait --wait-timeout 180 api worker
```

The database restart policy recovers unexpected exits. A service explicitly stopped by an operator still needs `docker compose up`. Do not delete database volumes to fix networking. Redact private data before sharing logs.
