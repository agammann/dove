# Deployment preparation

For the published ChatGPT Sites workspace, use the [hosted workspace guide](HOSTED-WORKSPACE.md). The Python application guidance and historical checks below describe a separate implementation.

The [public website](https://dove-paperwork.alx21.chatgpt.site) is live on OpenAI Sites. The full document workspace in this repository still requires its own deployment. Live provider validation and the [release checklist](RELEASE-CHECKLIST.md) must pass before customer onboarding.

## Chosen architecture

One Ubuntu LTS VM (4 GB RAM, 2 vCPU minimum for a small pilot) running Docker Compose: Caddy HTTPS reverse proxy, FastAPI serving the compiled React app, PostgreSQL 17 and one durable worker. Database and object volumes stay private; in the production override, API and database ports are exposed only within the Compose network. Encrypted off-host backups are required. A Hetzner shared VM is the reference option; another Docker-capable host can use the same configuration. The pilot starts with a volume-backed private object store. No S3 account, public bucket or mandatory cloud service is created.

This single-host design has downtime during maintenance and no automatic failover. It is a deliberate invitation-pilot operating assumption. Measure CPU/memory and model processing latency before increasing volume or concurrency.

## Local startup

Use the [first run guide](QUICKSTART.md) for local fixtures, ports, sample accounts and troubleshooting. The commands below target a Linux production host.

## Production configuration

1. After provisioning is explicitly authorized, create the host, choose a region agreed with pilot customers, install Docker from the official distribution, and restrict inbound traffic to SSH from administrators plus HTTPS/HTTP for Caddy. Do not expose PostgreSQL or private volumes.
2. Clone the reviewed source commit. Create an ignored `.env` on the server or inject environment values using the host secret manager. Generate a random `SECRET_KEY` of at least 40 characters and a strong `POSTGRES_PASSWORD`.
3. Set `ENVIRONMENT=production`, `PUBLIC_URL=https://your-approved-domain`, `MODEL_ADAPTER=openai`, `EMAIL_ADAPTER=resend`, `OPENAI_MODEL=gpt-4.1-mini`, and provide `OPENAI_API_KEY`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `EMAIL_FROM` and `REPLY_DOMAIN` securely. Never print or commit their values. Production validation refuses local adapters, short/default session secrets, HTTP origins or non-PostgreSQL databases.
4. Use secure OpenAI Developers setup in Codex for a new key, or the organization's approved secret-management process. Do not copy a key into chat. Set provider project usage caps/alerts in addition to Dove's per-work call allowance.
5. Verify a Resend sending domain and configure receiving MX records or a provider receiving domain. Set the dedicated reply domain. Register `/api/webhooks/resend` for `email.received`, `email.delivered`, `email.bounced` and `email.failed`; provide the signing secret server-side. DNS changes and provider configuration require review of the exact domain/account.
6. Put Caddy in front of the private API service using `deploy/Caddyfile` and the production Compose override. Set `DOVE_DOMAIN` to the approved hostname. HTTPS cookies and write-origin checks require matching `PUBLIC_URL`.
7. Start the stack, migrate once, check health, and issue a test invitation with the CLI. Do not seed samples in production. Run one authorized fictional document inference and email send/reply/attachment/delivery test to an explicitly authorized destination. Record provider IDs and outcomes without secrets.
8. Configure encrypted off-host backups and expiration, restore one into isolation, apply a deletion ledger before any recovery worker starts, then run the release checklist.

After configuring the approved host, DNS and secrets, use both Compose files for every production operation. In the Linux shell:

~~~sh
export COMPOSE_FILE=compose.yaml:compose.production.yaml
docker compose config --quiet
docker compose up --build --detach --wait --wait-timeout 180
docker compose ps
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/health').read().decode())"
~~~

Keep this `COMPOSE_FILE` setting in the deployment and backup environment. Running the base file alone starts the local topology. `config --quiet` validates configuration without printing resolved secret values. Check HTTPS health from outside the host too; internal health does not prove public routing or provider connectivity.

## Limits and cost assumptions

Per document: 8 MB, 50 PDF pages, 100,000 extracted characters. Per analysis input: 60,000 characters; per output: 4,000 tokens. Per work item: 20 reserved model calls and 15 outgoing message attempts, maximum two automatic reminders per request. At most 30 current documents, 30 generated line items and five recipients per package. Supported currencies: USD/EUR/GBP/CAD/AUD with two decimal places. The UI and API support multiple generated lines. Retained storage defaults are 512 MiB and 1000 objects per organization, 100 document versions and 20 package versions per work item, and 20 MiB per package. PDF processing has a 15 second timeout with Linux CPU and memory limits.

Cost planning, checked against official sources on 2026-09-08:

- GPT-4.1 mini: $0.40 per million input tokens and $1.60 per million output tokens. At 100 work items/month Ã— three analyses Ã— 8,000 input and 1,000 output tokens, modeled inference is **$1.44/month**. Large documents/retries can raise this; it is not measured pilot cost. [Official model pricing](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
- Resend lists 3,000 emails/month with a 100/day limit on Free, or $20/month for 50,000 emails on Pro; verify sending/receiving quotas and overages for the selected account before launch. Budget $0â€“$20/month for this small pilot, with no guarantee a free tier fits. [Official Resend pricing](https://resend.com/pricing/).
- Budget approximately â‚¬6â€“â‚¬15/month for a small shared VM, plus an explicit allowance for encrypted off-host backups, storage growth, domain renewal and applicable taxes. Region/currency/IP options change the exact quote; inspect it at provisioning time. [Official Hetzner pricing changes](https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/).
- Plan roughly **$15â€“$45/month equivalent before labor** as an initial operating allowance, not a provider quote or validated unit-economics claim. Track operator support/onboarding time separately; it will likely dominate a three-business pilot.

## Backup and restoration

`scripts/backup.py` pauses API and worker while taking a PostgreSQL custom-format dump and object archive, writes checksums, then restarts them. Use a new output directory each time. Copy the archive to an encrypted off-host destination only after checking its access controls. Local artifacts remain sensitive.

```sh
python scripts/backup.py --output /secure-backups/dove-YYYYMMDD
python scripts/verify_restore.py /secure-backups/dove-YYYYMMDD
```

On Linux, install Python 3.12 or newer for these scripts and retain the production Compose file setting above. The scripts invoke Docker Compose and inherit its environment.

The verification script restores into a generated disposable database, extracts objects into a temporary directory, validates document and package hashes and ZIP integrity, never starts a worker, then drops only that generated database. It does not overwrite the live database. For disaster recovery, restore into a fresh stack first, review canceled/deleted work and uncertain deliveries, apply the deletion ledger, and keep automation paused until sign-off. Document measured recovery time and recovered record counts in the validation report.

## Rollback and teardown

Record source commit and image digest for each deployment. Back up before migrations. For code-only rollback, stop API/worker, deploy the previous known compatible image and restart after health checks. For incompatible schema rollback, restore the corresponding pre-migration backup into an isolated stack, validate and deliberately cut over; do not run blind destructive migration downgrades against customer data.

`docker compose down` stops this stack and preserves volumes. Removing its volumes is destructive: obtain explicit approval, verify the exact project/volume names, retain the agreed export/backup, then remove only Dove's volumes. Revoke only Dove's provider credentials/webhook/DNS records after checking ownership. Delete encrypted backups under the agreed expiration policy. No unrelated project resources should be changed.
