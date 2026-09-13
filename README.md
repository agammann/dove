# Dove

From completed work to completed paperwork.

**[Visit Dove’s public website](https://dove-paperwork.alx21.chatgpt.site)** · [Request early access](https://dove-paperwork.alx21.chatgpt.site/#access)

Dove helps businesses resolve missing purchase orders, acceptance evidence and approved deliverables before invoicing. It runs one configurable workflow across separate organization workspaces.

![Dove reviewing fictional source evidence](frontend/public/product-screenshot.png)

Upload readable PDF/TXT documents, inspect proposed requirements and source excerpts, authorize requests to customer contacts, review incoming evidence, and approve an exact billing package before separately authorizing delivery. Provider acceptance is recorded separately from confirmed delivery, customer acceptance and payment.

## Public website

Dove’s public website and working early access form are hosted on OpenAI Sites. The website is available independently of a local development computer. The full document processing workspace in this repository still requires a separate production deployment and live provider setup before customers can sign in.

Website submissions are stored in the Sites database for manual review. They do not create app accounts or send automatic email notifications.

## Run locally

Install Docker with the Linux engine and Docker Compose v2. From this repository:

```sh
docker compose up --build -d
docker compose exec api python -m dove.cli seed
```

Open [Dove locally](http://127.0.0.1:8000). The default model fixture and email outbox are explicitly simulated. No provider key or external email is needed for local development. PostgreSQL and private objects persist in named volumes; API and worker are separate processes.

| Sample workspace | Email |
| :--- | :--- |
| Design studio | studio@dove.example |
| Consulting firm | consulting@dove.example |
| IT provider | it@dove.example |

All three fictional local accounts use `Dove-local-sample-2026!`. The login page has sample selection buttons. These accounts are restricted to local fixture mode.

## Sample walkthrough

If port 8000 is occupied, set both `DOVE_PORT=8010` and `PUBLIC_URL=http://127.0.0.1:8010` in an ignored root `.env` before starting Compose, then open port 8010.

1. Select Design studio and sign in. Open Brand identity handoff.
2. Inspect each requirement and source excerpt. Review acceptance, deliverables, amount and billing recipient as satisfied with an explanation. Leave the missing purchase order unresolved.
3. Confirm the checklist. Optionally draft and edit the request. Select the authorized contact, grant follow up permission, and authorize the missing item request.
4. Open Resolve. The local outbox records simulated provider acceptance. Expand Local inbox and submit the provided fictional purchase order reply.
5. The worker persists and associates the reply, stops reminders and creates a human decision. Resolve the decision after inspecting the source, then mark the purchase order requirement satisfied with its incoming evidence.
6. Open Package. Generate one confirmed USD 2400.00 line from the reviewed amount evidence, or upload and attach an existing invoice PDF. Enter issue and due dates, completion summary and exact recipients. Confirm details and build the package.
7. Preview the exact invoice and manifest, download the ZIP, approve the exact package, then separately authorize delivery. The local outcome is simulated provider acceptance.

The consulting sample exposes conflicting amounts. The IT sample needs acceptance and a completion checklist. Documents uploaded as internal evidence are excluded from outgoing packages. Supporting documents require explicit delivery approval.

Reset only the three fictional sample organizations:

```sh
docker compose exec api python -m dove.cli reset-samples
```

This removes sample work and recreates the fictional examples. It refuses production mode and non-sample organizations. Stop this stack while preserving its volumes with `docker compose down`.

## Accounts and operations

The application’s own landing form saves access requests in its application database for manual operator review. The commands below manage that application database; requests from the public OpenAI Sites website are reviewed separately through Sites. Account creation requires a private invitation:

```sh
docker compose exec api python -m dove.cli access-requests
docker compose exec api python -m dove.cli invite --organization "Example Business" --email "operator@example.com"
```

The invitation command creates a 72 hour single use token and prints a private link. Share it only with the intended recipient. New organizations begin with automation paused. Authentication uses pwdlib Argon2 and expiring hashed sessions. All operators within an organization have the same permission level.

Health endpoint: `/api/health`. Worker failures appear on the work item with a manual retry where permitted. Pausing stops pending automation. Uncertain sends are quarantined and must be reconciled before any retry.

## Tests and development

Run the isolated SQLite suite inside the built Linux image:

```sh
docker compose run --rm --no-deps api python -m pytest tests -q
```

For PostgreSQL, create a dedicated disposable database. Never point the test suite at the application database: test fixtures recreate all tables in the selected test database.

```sh
docker compose exec db createdb -U dove dove_test
docker compose run --rm --no-deps -e TEST_DATABASE_URL=postgresql+psycopg://dove:local-dove-password@db/dove_test api python -m pytest tests -q
```

That URL is the local example only. If the database already exists, skip its creation. With a custom local password, supply the test connection securely through environment configuration.

For native development, use Python 3.12, Node 22 and pnpm 10.16.1. Install `backend/requirements.lock` with `pip install --require-hashes -r requirements.lock` in a virtual environment. Run Alembic and the API from `backend`; use the same database and storage settings for `python -m dove.worker`. In `frontend`, run `pnpm install --frozen-lockfile` and `pnpm dev`. The supported full workflow uses the same origin from the compiled frontend served by FastAPI. Linux containers are required for production PDF memory and CPU enforcement; native Windows development still has the child process timeout and admission limit.

## Release documents

| Document | Purpose |
| :--- | :--- |
| [Architecture](docs/ARCHITECTURE.md) | Domain model, authority and recovery |
| [Deployment](docs/DEPLOYMENT.md) | Hosting, provider configuration, costs, backups, rollback and teardown |
| [Data handling](docs/DATA-HANDLING.md) | Provider destinations, retention and deletion |
| [Validation](docs/VALIDATION.md) | Observed test outcomes and limitations |
| [Release checklist](docs/RELEASE-CHECKLIST.md) | Remaining invitation beta gates |
| [Pilot kit](docs/PILOT-KIT.md) | Interviews, onboarding, feedback, scorecard and pricing hypothesis |
| [Progress](PROGRESS.md) | Current implementation and external dependencies |

The repository is public at the owner's request. No open source license has been selected for Dove's original source. Dependency licenses remain applicable; supplied notices are retained in `THIRD-PARTY-NOTICES`.
