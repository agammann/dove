# Dove on ChatGPT Sites

[Website](https://dove-paperwork.alx21.chatgpt.site) · [Workspace](https://dove-paperwork.alx21.chatgpt.site/workspace) · [Public source](https://github.com/agammann/dove)

From completed work to completed paperwork.

This is the Sites-native Dove website and invitation workspace. It runs a JavaScript Worker with D1 records, private R2 documents, Sign in with ChatGPT, and browser model analysis. The separate Python/PostgreSQL application remains available in the parent repository.

## Use Dove

1. Open the workspace and sign in with ChatGPT. Redeem your private invitation; the access request form does not create an account.
2. In Settings, enter the business name and billing details. Uncheck the automation pause when ready.
3. Create a work item with a verified customer billing contact. Upload text-readable PDFs or TXT documents.
4. Choose Analyze documents. A model on your device proposes requirements with exact source quotes. Review every item; only you can mark it satisfied or waived.
5. Assemble a package using a source-supported total. Supply an existing PDF invoice, or generate a simple invoice with one confirmed total. Confirm tax treatment yourself.
6. Open the invoice PDF and download the ZIP. Review the actual files before approving the exact version.
7. Download the approved package for your existing delivery process. Configured email delivery is a separate explicit authorization.

A new document or checklist edit invalidates package approvals. Files and records are private to workspace members. All members have the same access and approval permissions. Analysis runs on the visitor’s device. Source documents remain in private R2 storage and saved proposals go back to the workspace server for exact-quote and revision checks. Model assets download from public hosts; hosting and asset hosts may process normal request metadata. No paid AI API is used.

## Current limits

- 4 MB per PDF/TXT; 40 PDF pages; 10 documents and 200,000 extracted characters per work item.
- 100 work items; 100 stored objects and 64 MB per workspace. Package ZIPs and invoice copies count toward storage.
- No paid AI analysis quota. Browser analysis reads every source section and proposes at most 20 requirements; larger checklists require manual review. General workspace mutation limits still apply.
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

No OPENAI_API_KEY or OPENAI_MODEL is needed. Browser analysis requires WebGPU, sufficient graphics memory and model downloads. Development sign-in uses the starter's fixed local identity, seedy@sites.test; it exists only in the Vite development server. Production authentication is supplied by Sites.

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

Configure DOVE_ADMIN_TOKEN as a server secret. Remove unused OPENAI_API_KEY and OPENAI_MODEL variables; they are not read by the analysis flow. DOVE_ADMIN_TOKEN should be a random 32-byte value, kept only by the site operator. Never put credentials in frontend code or Git. Site environment changes apply with the next deployment.

To create a real workspace, run create-workspace.mjs with the business name and its owner's ChatGPT email. The default URL is the public Dove site. Share the resulting invitation privately. Omitting email creates an unbound single-use owner invitation: whoever redeems it first receives access. Use email-bound invitations for customers. Teammates can be invited from Settings.

Public interest submissions are in the separate access_requests D1 table. They neither create accounts nor send email. Review deletion requests, verify identity and apply the 90-day retention policy stated on the website.

Workspace export downloads records and extracted text; original uploads and package binaries must be downloaded separately. There is no complete hosted disaster-recovery/restore workflow yet. Deleting a work item immediately hides its files and queues storage cleanup for that request and subsequent workspace visits; this is permanent.

### Optional email

Set RESEND_API_KEY and EMAIL_FROM only after verifying the sender domain and testing with an explicitly authorized recipient. Missing-document requests also require REPLY_DOMAIN. Incoming messages are not automatically ingested: the operator must receive and verify replies externally. Do not configure a reply domain without a working mailbox/routing destination.

A provider-accepted response is not proof of delivery, customer acceptance or payment. An uncertain attempt is not automatically retried. Reconcile it in the provider dashboard using the stored request/package ID and idempotency key before any manual recovery. Delivery of a package is authorized at the moment its send attempt is recorded and uses its immutable stored bytes.

## Verification evidence

Historical provider edition, September 19, 2026: Local HTTP integration checks passed using fictional data and live OpenAI analysis. Checks covered invitation membership, anonymous access, quote validation, human review, total/date validation, ZIP contents and digest, actual PDF text extraction, stale package rejection, approval and unconfigured-email denial. Browser review confirmed saved work and package controls. This evidence does not establish real-customer usability or email operation.

See the repository's hosted-workspace validation notes for production verification and remaining limits.


### Repeat the integration check

The verification script uses Python 3.12+ and httpx 0.28.1 (available in the parent Python application development environment). Build, initialize the local database, and run `node scripts/preview-built.mjs` in one terminal; run `python scripts/verify-local.py` in another. It refuses remote URLs and creates fictional workspaces. It saves source-linked browser proposal fixtures and retains test records in local storage. Real browser model generation is checked separately. Results and a package ZIP are saved under ignored outputs/. This tests the actual built Worker with local identity headers; it does not bypass or reproduce production sign-in.

The esbuild override applies to Drizzle's legacy loader. Schema generation was rerun after the override and reported no changes. Full dependency audit reported zero known advisories at verification time.

## Browser migration

The first run downloads model files from public hosts. Text generation runs in a dedicated browser worker using WebLLM; prompts are not sent to a hosted model. Document analysis defaults to Qwen 3 4B. Smaller Qwen 3 1.7B and Llama 3.2 1B choices use less memory but can produce weaker proposals. Model downloads are cached when browser storage permits.

Use HTTPS (or localhost) and a current browser with WebGPU and compatible graphics hardware. A model choice does not guarantee that every device has enough memory. Download speed, inference speed and answer quality depend on the device and model. Stop a download or generation from the interface; errors preserve existing inputs. There is no paid model fallback. Hosting and model-download bandwidth remain separate from AI API fees.

Model proposals cannot mark requirements satisfied or waived. Saving requires the original work revision and server-verified quotes; changes made during analysis cause a conflict instead of overwriting newer work. Stop analysis preserves the existing checklist. Analysis is grouped into source sections so documents are not silently truncated. Review duplicates and cross-document conflicts manually. Authentication, invitations, private files, package approvals and explicit email authorization remain in place.
