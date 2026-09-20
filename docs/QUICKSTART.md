# First run

[Back to Dove](../README.md) Â· [Documentation](README.md)

Use fictional documents in local mode. Analysis and email are simulated; the public website is a separate service.

## Prerequisites

Install Git and Docker with its Linux container engine. Start Docker, then confirm `docker version` shows a server and `docker compose version` succeeds. Use a current Compose plugin supporting `--wait`. Docker installs Python, Node and pnpm inside the image; those tools are not required on the host for this route.

```sh
git clone https://github.com/agammann/dove.git
cd dove
```

Run all following commands beside `compose.yaml`.

## Choose a local address

The default app address is `http://127.0.0.1:8000`; PostgreSQL uses loopback port 54329. No `.env` is needed for the defaults. If app port 8000 is occupied, copy `.env.example` to `.env` and change both lines before startup:

```dotenv
DOVE_PORT=8010
PUBLIC_URL=http://127.0.0.1:8010
```

Keep `ENVIRONMENT=local`, `MODEL_ADAPTER=fixture`, and `EMAIL_ADAPTER=local`. Review an existing `.env` before editing it. Always open exactly `PUBLIC_URL`: `localhost` and `127.0.0.1` are different origins.

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

To deliberately delete and recreate only the three fictional sample workspaces, use `docker compose exec api python -m dove.cli reset-samples`. It refuses production mode and non-sample organizations. This is not a networking repair command.

## Troubleshooting

| Symptom | Action |
| :--- | :--- |
| Docker daemon unavailable | Start Docker and confirm the Linux engine. |
| Unknown `--wait` option | Update Docker Compose. |
| Port 8000 occupied | Set both alternate port values above, then rerun startup. |
| Port 54329 occupied | Identify the conflicting service; change only Dove's loopback host port in `compose.yaml`, keeping container port 5432. |
| Writes return 403 | Match the browser address exactly to `PUBLIC_URL`, then restart after environment changes. |
| API unhealthy | Inspect `docker compose logs --tail=80 api db` before seeding. |
| Pending work | Check worker logs and work/organization pause settings. |

If PostgreSQL is healthy but the API reports `failed to resolve host 'db'` after a Docker interruption, recreate only the app containers, preserving volumes:

```sh
docker compose up --detach --force-recreate --wait --wait-timeout 180 api worker
```

The database restart policy recovers unexpected exits. A service explicitly stopped by an operator still needs `docker compose up`. Do not delete database volumes to fix networking. Redact private data before sharing logs.
