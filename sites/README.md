# Dove on ChatGPT Sites

[Website](https://dove-paperwork.alx21.chatgpt.site) · [Workspace](https://dove-paperwork.alx21.chatgpt.site/workspace) · [Public source](https://github.com/agammann/dove)

From completed work to completed paperwork.

This is the Sites-native Dove website and invitation workspace. It runs a JavaScript Worker with D1 records, private R2 documents, Sign in with ChatGPT, and server-side OpenAI analysis. The separate Python/PostgreSQL application remains available in the parent repository.

## Use Dove

1. Open the workspace and sign in with ChatGPT. Redeem your private invitation; the access request form does not create an account.
2. In Settings, enter the business name and billing details. Uncheck the automation pause when ready.
3. Create a work item with a verified customer billing contact. Upload text-readable PDFs or TXT documents.
4. Choose Analyze documents. OpenAI proposes requirements with exact source quotes. Review every item; only you can mark it satisfied or waived.
5. Assemble a package using a source-supported total. Supply an existing PDF invoice, or generate a simple invoice with one confirmed total. Confirm tax treatment yourself.
6. Open the invoice PDF and download the ZIP. Review the actual files before approving the exact version.
7. Download the approved package for your existing delivery process. Configured email delivery is a separate explicit authorization.

A new document or checklist edit invalidates package approvals. Files and records are private to workspace members. All members have the same access and approval permissions. Every AI analysis transmits extracted document text to OpenAI with storage disabled at the API request level; this does not make a claim about all provider retention policies.

## Current limits

- 4 MB per PDF/TXT; 40 PDF pages; 10 documents and 200,000 extracted characters per work item.
- 100 work items; 100 stored objects and 64 MB per workspace. Package ZIPs and invoice copies count toward storage.
- 20 AI analyses per work item and 50 per workspace per UTC day.
- 30 checklist requirements, 10 package versions and 10 outgoing requests per work item.
- 40 mutations per workspace per minute. Open invitations expire after 72 hours; at most 20 retained invitations.
- Generated invoices have a single confirmed total. Itemized tax calculation, OCR, accounting synchronization, payment collection and granular roles are not included.
- Email delivery requires a configured sending service and verified sender. **Incoming email webhooks and automatic scheduled reminders are not implemented in this Sites version.** Upload externally received documents or manually record verified reply text.

## Local development

Requires Node.js 22.13 or newer and npm. Run these commands in this directory:

~~~sh
npm ci
node scripts/init-local.mjs
npm run build
node node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_aromatic_psylocke.sql
node node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0001_unknown_talisman.sql
npm run dev
~~~

Apply each migration only once to a local database. Check the actual filenames in drizzle/ before executing. Migration files are append-only; never rewrite an applied migration.

Add OPENAI_API_KEY to the ignored .env.local file before testing live analysis. Do not use a NEXT_PUBLIC_ prefix. Development sign-in uses the starter's fixed local identity, seedy@sites.test; it exists only in the Vite development server. Production authentication is supplied by Sites.

In a second terminal, create the local sample workspace:

~~~sh
node scripts/create-workspace.mjs --name="Fictional Studio" --email="seedy@sites.test" --url=http://localhost:5173
~~~

Open the private invitation file printed by the command. No email is sent.

~~~sh
npx tsc --noEmit
npm run lint
npm run build
~~~

## Production operations

Existing project metadata is in .openai/hosting.json. Preserve its ID when updating Dove. For an independent fork, provision a different Sites project and use its returned metadata; copying this source does not grant access to Dove's production resources.

Configure OPENAI_API_KEY and DOVE_ADMIN_TOKEN as server secrets and OPENAI_MODEL as a normal server variable. DOVE_ADMIN_TOKEN should be a random 32-byte value, kept only by the site operator. Never put credentials in frontend code or Git. Site environment changes apply with the next deployment.

To create a real workspace, run create-workspace.mjs with the business name and its owner's ChatGPT email. The default URL is the public Dove site. Share the resulting invitation privately. Omitting email creates an unbound single-use owner invitation: whoever redeems it first receives access. Use email-bound invitations for customers. Teammates can be invited from Settings.

Public interest submissions are in the separate access_requests D1 table. They neither create accounts nor send email. Review deletion requests, verify identity and apply the 90-day retention policy stated on the website.

Workspace export downloads records and extracted text; original uploads and package binaries must be downloaded separately. There is no complete hosted disaster-recovery/restore workflow yet. Deleting a work item immediately hides its files and queues storage cleanup for that request and subsequent workspace visits; this is permanent.

### Optional email

Set RESEND_API_KEY and EMAIL_FROM only after verifying the sender domain and testing with an explicitly authorized recipient. Missing-document requests also require REPLY_DOMAIN. Incoming messages are not automatically ingested: the operator must receive and verify replies externally. Do not configure a reply domain without a working mailbox/routing destination.

A provider-accepted response is not proof of delivery, customer acceptance or payment. An uncertain attempt is not automatically retried. Reconcile it in the provider dashboard using the stored request/package ID and idempotency key before any manual recovery. Delivery of a package is authorized at the moment its send attempt is recorded and uses its immutable stored bytes.

## Verification evidence

September 19, 2026: Local HTTP integration checks passed using fictional data and live OpenAI analysis. Checks covered invitation membership, anonymous access, quote validation, human review, total/date validation, ZIP contents and digest, actual PDF text extraction, stale package rejection, approval and unconfigured-email denial. Browser review confirmed saved work and package controls. This evidence does not establish real-customer usability or email operation.

See the repository's hosted-workspace validation notes for production verification and remaining limits.


### Repeat the integration check

The verification script uses Python 3.12+ and httpx 0.28.1 (available in the parent Python application development environment). Build, initialize the local database, and run `node scripts/preview-built.mjs` in one terminal; run `python scripts/verify-local.py` in another. It refuses remote URLs and creates fictional workspaces. It makes a live OpenAI call and retains test records in local storage. Results and a package ZIP are saved under ignored outputs/. This tests the actual built Worker with local identity headers; it does not bypass or reproduce production sign-in.

The esbuild override applies to Drizzle's legacy loader. Schema generation was rerun after the override and reported no changes. Full dependency audit reported zero known advisories at verification time.
