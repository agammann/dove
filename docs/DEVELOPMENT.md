# Development

[Back to Dove](../README.md) · [Documentation](README.md)

Follow [first run](QUICKSTART.md) first. Docker commands below run from the repository root.

## Rebuild and test

Compose uses built images, not live source mounts. After code changes:

```sh
docker compose up --build --detach --wait --wait-timeout 180
docker compose run --rm --no-deps -T api python -m pytest tests -q
```

The default fixture uses a temporary SQLite database and object directory, with simulated model/email adapters. It does not use the application's database.

For PostgreSQL checks, use a dedicated disposable database. Test fixtures drop and recreate tables in the database selected by `TEST_DATABASE_URL`. Never select the application or a production database.

With the default local database password:

```sh
docker compose exec db createdb -U dove dove_test
docker compose run --rm --no-deps -T -e TEST_DATABASE_URL=postgresql+psycopg://dove:local-dove-password@db/dove_test api python -m pytest tests -q
```

If that database already exists, confirm it is disposable before testing. With a custom password, configure the test connection securely instead of copying the example URL.

## Native development

Use Python 3.12, Node 22 and pnpm 10.16.1. Docker is the supported full workflow and provides Linux PDF resource limits. Run native development in a clean terminal without production environment variables.

From `frontend/`:

```sh
corepack enable
corepack prepare pnpm@10.16.1 --activate
pnpm install --frozen-lockfile
pnpm build
```

From `backend/`, create a Python virtual environment and activate it. On Windows use `py -3.12 -m venv .venv` then `.\.venv\Scripts\Activate.ps1`. On macOS/Linux use `python3.12 -m venv .venv` then `. .venv/bin/activate`. In that environment:

```sh
python -m pip install --require-hashes -r requirements.lock
python -m alembic upgrade head
python -m dove.cli seed
python -m uvicorn dove.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, activate the same environment, enter `backend/` and run `python -m dove.worker`. Open `http://127.0.0.1:8000`. Both processes must share database, storage and origin settings. Native defaults use `backend/.data/`; the root Compose `.env` is not automatically loaded when running from `backend/`. If port 8000 is occupied, stop your local Docker stack or align the native server port and `PUBLIC_URL`.

Run `python -m pytest tests -q` from `backend/` for native tests. From `frontend/`, `pnpm check` checks TypeScript and `pnpm build` compiles the UI. Preserve both dependency lockfiles.

`pnpm dev` is optional: it proxies `/api` to port 8000. The backend's `PUBLIC_URL` must match the exact Vite origin, including its actual port. Restart the backend after environment changes. The documented full workflow uses the compiled frontend served by FastAPI.

## Before publication

Use fictional verification data, run relevant checks, validate documentation links, and exclude credentials, uploads, databases, exports and backups from Git. Distinguish local fixtures from live provider results. See [validation](VALIDATION.md) and [release gates](RELEASE-CHECKLIST.md).
