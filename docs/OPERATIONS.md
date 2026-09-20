# Operations

For the published ChatGPT Sites workspace, use the [hosted workspace guide](HOSTED-WORKSPACE.md). The Python application guidance and historical checks below describe a separate implementation.

[Back to Dove](../README.md) · [Documentation](README.md)

Run local commands beside `compose.yaml`. For production, use the same Compose files and environment that started the deployment.

## Access requests

| Source | Review location |
| :--- | :--- |
| Public OpenAI Sites website | Owner access to the site's `access_requests` database table in Sites |
| Landing page served by this Python app | Application database through the CLI |

Neither form creates an account automatically. The public site sends no automatic email notifications and does not copy submissions into the app database. Review deletion requests and retention according to its data notice.

```sh
docker compose exec api python -m dove.cli access-requests
```

This prints private contact details from the application's database only. It cannot read the Sites database.

## Invitations

Replace the example business and recipient:

```sh
docker compose exec api python -m dove.cli invite --organization "Example Business" --email "operator@example.com"
```

The command reuses an organization with that exact name or creates one if absent. It prints a private single use link expiring in 72 hours; it does not send email. Share it only with the intended recipient. Invitation URLs use the application's `PUBLIC_URL`, not the separate marketing website. New organizations start with automation paused; all operators in an organization have the same permission level.

## Health and recovery

```sh
docker compose ps
docker compose logs --tail=80 api worker
docker compose exec api python -m dove.cli --help
```

The API health endpoint checks API/database connectivity. Inspect the worker separately. For pending work, check pause state, job status and allowance. Uncertain sends require reconciliation before another attempt.

Database and object volumes persist across `docker compose down`. Do not remove them to repair networking. Follow [backup and restoration](DEPLOYMENT.md#backup-and-restoration) before migrations or recovery, and reconcile deleted work and uncertain deliveries before restarting a restored worker.
