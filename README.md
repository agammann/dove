# Dove

From completed work to completed paperwork.

**[Open Dove](https://dove-paperwork.alx21.chatgpt.site/workspace)** · **[Visit the website](https://dove-paperwork.alx21.chatgpt.site)** · **[Browser workspace guide](docs/HOSTED-WORKSPACE.md)**

Dove helps service businesses gather missing purchase orders, review acceptance evidence and assemble an approved billing package after the work is finished. The browser workspace needs no login or ChatGPT account. Documents and work are saved on the visitor’s device. Device analysis and manual review require no API key; optional hosted analysis uses the visitor’s own OpenAI key and API billing.

![Dove browser workspace with fictional documents](sites/public/product-screenshot.png)

## Try a fictional job

Follow the [browser quickstart](docs/BROWSER-QUICKSTART.md) to upload the included examples, review a checklist manually, generate an invoice, approve the exact package and restore a complete backup. The walkthrough needs no model or API key.

For development, enter `sites/`, run `npm ci` and `npm run dev`, then open `http://127.0.0.1:5173/workspace/`. Node.js 22.13 or newer is required. See [browser development](sites/README.md#local-development) for builds and checks.

Download the v1 source ZIP from [Releases](https://github.com/agammann/dove/releases), verify `SHA256SUMS`, and extract it before using those commands. The ZIP includes both the browser workspace and separate Docker sample.

## What is available

| Part | Status |
| :--- | :--- |
| Public website | Live, with direct access to the browser workspace |
| Application in this repository | Runnable locally with fictional samples and simulated model and email adapters |
| Browser workspace | No login; local documents, device or visitor-funded hosted analysis, evidence review, PDF/ZIP packages and complete backup export/import |

The published website source is in [sites/](sites/README.md). Open it and start: no account or invitation is required. Files, extracted text and decisions stay in IndexedDB in that browser profile. Device analysis downloads public model assets on first use and requires WebGPU and enough graphics memory. Hosted analysis sends the complete document text, filenames and work context through this server to OpenAI in one paid request using your key, with GPT-5.4 selected by default. It accepts up to 32,000 extracted characters and proposes up to 20 requirements with one to three source quotes each. Quotes preserve source words while normalizing whitespace. New hosted conflicts use a neutral review title while preserving the model’s reason, status and citations. A hosted missing-information result means the model did not identify information, not that its absence was proved. Review the complete originals and source omissions before assembly and approval. Oversized work is not partially sent; use device analysis or manual review. Keys stay in tab memory and are excluded from saved workspace data and backups. Manual review and packaging work without loading or calling a model.

Review the original documents for omissions, and compare invoice dates with agreed payment terms before approval. A fully reviewed checklist covers its recorded items; it does not establish that analysis found every requirement. See the [October 3 hosted-analysis and manual-review verification](docs/verification/hosted-invoice-timing-2026-10-03.md) for the separate first-response results, retained failures and manual checks. The [browser build verification](docs/verification/browser-build-migration-2026-10-03.md) records local build and native browser-tool checks separately from published-site and model results.

**Back up your work in Settings.** Export includes original files and packages; restore replaces the local workspace and requires renewed package approval. Clearing browser data can erase saved work. There is no automatic sync, teammate access or email delivery. Backup ZIPs and local records are not encrypted by Dove. See the [browser workspace guide](docs/HOSTED-WORKSPACE.md).

The Python sample below remains a separate implementation with its own accounts and optional providers. Existing hosted records were not deleted or made public by the browser migration.

## Run the local Python sample

Install Git and Docker with the Linux engine and a current Docker Compose plugin. Docker supplies Python, Node and the application dependencies.

```sh
git clone https://github.com/agammann/dove.git
cd dove
docker compose up --build --detach --wait --wait-timeout 180
docker compose exec api python -m dove.cli seed
```

Run the seed command only after startup succeeds. Open `http://127.0.0.1:8000`, choose **Design studio**, and sign in with the fictional sample password `Dove-local-sample-2026!`. No API key or real email is required.

If port 8000 is occupied, configure an alternate port **before startup** using the [first run guide](docs/QUICKSTART.md#choose-a-local-address). That guide covers prerequisites, sample accounts, expected health output, the walkthrough, stopping the app and troubleshooting.

## Separate Python sample workflow

1. **Gather:** Upload readable PDF or TXT documents for a completed job.
2. **Review:** Inspect proposed requirements beside source excerpts and resolve conflicting evidence.
3. **Resolve:** Review and authorize a missing item request, then review the reply and supporting documents.
4. **Package:** Check invoice lines, recipients and attachments. Approve the exact package, then separately authorize delivery.

Provider acceptance, confirmed email delivery, customer acceptance and payment are distinct states. The local sample stops at simulated provider acceptance.

## Documentation

| I want to… | Guide |
| :--- | :--- |
| Use the hosted workspace | [Hosted Dove](docs/HOSTED-WORKSPACE.md) |
| Run the sample and troubleshoot setup | [First run](docs/QUICKSTART.md) |
| Change code or run checks | [Development](docs/DEVELOPMENT.md) |
| Operate the separate Python application | [Operations](docs/OPERATIONS.md) |
| Prepare a production host and backups | [Deployment](docs/DEPLOYMENT.md) |
| Understand implementation and data handling | [Documentation index](docs/README.md) |
| Review evidence and unfinished release work | [Validation](docs/VALIDATION.md), [release checklist](docs/RELEASE-CHECKLIST.md), [progress](PROGRESS.md) |

## Repository layout

| Path | Contents |
| :--- | :--- |
| `sites/` | Published browser workspace, backup tools, retained legacy migrations and verification |
| `backend/` | FastAPI application, worker, migrations, locked Python dependencies and tests |
| `frontend/` | React interface, Vite configuration and pnpm lockfile |
| `deploy/` | Production reverse proxy configuration |
| `scripts/` | Backup, isolated restore verification and dependency notice collection |
| `docs/` | Setup, development, operations, architecture and release guidance |
| `THIRD-PARTY-NOTICES/` | Dependency licenses and notices |

## Scope and source terms

Dove v1 supports browser document review and billing packages on one device, with complete backup and restoration. The Python application remains a separately runnable example; its live email and provider setup is outside browser v1. OCR, mailbox synchronization, accounting integrations, tax decisions, payment collection and granular organization roles are outside this release.

Dove's original source is available under the [MIT license](LICENSE). Dependency licenses and [notices](THIRD-PARTY-NOTICES/README.md) remain applicable. Read [v1 scope, upgrading and recovery](docs/STABILITY.md) before changing a saved workspace.
