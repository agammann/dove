# Dove — browser workspace

[Open Dove](https://dove-paperwork.alx21.chatgpt.site/workspace) · [Website](https://dove-paperwork.alx21.chatgpt.site) · [Source](https://github.com/agammann/dove)

From completed work to completed paperwork. Dove opens directly in your browser: **no login, no ChatGPT account and no invitation**. Device analysis and manual review need no API key. Optional OpenAI analysis uses your own API key and is billed to your account.

## Use Dove

1. Open the workspace. In Settings, enter your business name and billing details for invoices.
2. Create a work item and verify its customer billing contact. The contact email is an invoice field, not a login.
3. Add readable PDF or TXT documents. Originals and extracted text are saved in this browser profile.
4. Choose **On this device** and select **Analyze documents**, or choose **OpenAI with your key**, enter your key and select **Analyze with OpenAI**. You can also add requirements manually. Review exact source quotes; only you can mark requirements satisfied or waived.
5. Save missing-document request drafts. Send them through your own email, then record verified replies or add the received documents. Dove sends no email.
6. Assemble a package with a source-supported total. Supply an existing invoice PDF or generate a simple invoice. Download and inspect the invoice and ZIP before approving that exact version.
7. Deliver the approved ZIP through your existing process. Dove does not track delivery, acceptance or payment.

New documents and checklist edits invalidate earlier package approvals. Source quotes, work revisions, amounts and dates are checked locally. AI suggestions cannot approve work.

## Storage and complete backups

Documents, files, packages, settings and decisions are stored in **IndexedDB in this browser profile**, not in a hosted workspace database. There is no automatic cross-device sync or shared workspace. Anyone using the same profile can open its records. Dove does not encrypt local records or backup ZIPs.

In Settings, choose **Export complete backup** regularly and before clearing browser data. The ZIP includes original uploads, extracted text, saved decisions, generated invoices and package ZIPs. Store it privately outside browser storage. To move devices, open Dove in the new browser and choose **Restore backup**.

Restoring replaces the entire current local workspace after validating the archive and file hashes. Export existing work first. Invalid backups leave current work unchanged. Restored packages require renewed approval. A backup is not a signed or tamper-proof audit record.

Browser cleanup, private browsing, storage eviction, a different profile, or a different site address can make saved work unavailable. The optional **Request persistent storage** button asks the browser to reduce eviction; it is not a backup guarantee.

## Browser analysis

Device analysis uses WebLLM in a dedicated browser worker. The default model is Qwen 3 4B; Qwen 3 1.7B needs less graphics memory but may produce weaker proposals. First use downloads model files from public hosts. In device mode, prompts and document text are not sent to a paid AI service. Hosting and model-download hosts may process ordinary request metadata.

Use HTTPS or localhost, WebGPU and compatible hardware with enough graphics memory. Speed, download size and quality depend on the model and device. Cached assets may be evicted. The hosted website still needs a connection to load; Dove is not a guaranteed offline-installable application. Manual review and packaging do not require loading a model. Device mode never switches to paid analysis automatically.

Device analysis processes source sections and proposes at most six requirements per section and 20 overall. Review omissions, duplicates and cross-document conflicts yourself. Cancellation preserves the previous checklist; work changed during analysis cannot be overwritten by stale results.

## Optional hosted analysis

Choose **OpenAI with your key** explicitly to use GPT-5.4 (the default) or GPT-5.4 mini without a local model download. Each analysis reads all documents together in one paid request; your OpenAI account pays for usage. Hosted analysis accepts up to 32,000 extracted characters across the work item. The interface shows the character count and rejects larger work before sending anything; it never silently truncates documents. Use device analysis or review larger work manually. Check [current API pricing](https://openai.com/api/pricing/) before analyzing large documents. The server uses a fixed OpenAI endpoint and only the key supplied with that request. There is no owner-key or environment-key fallback.

This mode sends the complete extracted document text and filenames, plus the work title, customer and description, through the Dove server to OpenAI. Work context identifies the job but does not count as source evidence. The API request uses `store: false`; OpenAI's applicable data policies still apply. Your key stays in tab memory and is sent in an authorization header. It is excluded from IndexedDB, workspace backups and saved proposals. Clear it with **Clear key**, switch back to device mode or reload the page. The application does not log the key.

Cancellation preserves the previous checklist, but usage already incurred can still be billed. Invalid keys, provider errors and unverified source quotes cannot save replacement analysis. Hosted results can contain up to 20 requirements with one or two quotes each. Quotes preserve source words while normalizing line breaks and repeated spaces, and must match the cited document and page. The existing revision and human-approval checks still apply. A stronger model can still omit requirements or miss conflicts; review the documents yourself.

## Limits

- PDF/TXT: 4 MB per file, 40 PDF pages, 100,000 extracted characters per document; no OCR for scanned pages.
- Work item: 10 documents, 200,000 extracted characters, 30 requirements, 10 package versions and 10 request drafts. Hosted analysis has a separate 32,000-character limit across all documents and proposes at most 20 requirements.
- Workspace: 100 work items, 100 stored files and 64 MB of file contents. Record text is limited to 19 MB per workspace and 450,000 characters per work item. Actual browser quota can be smaller.
- Generated invoices contain one confirmed total. Confirm tax treatment yourself; itemized accounting, payments, automated email and reminders are not included.
- Backup ZIP: up to 90 MB on import, with bounded records/files and integrity checks. Only the complete browser-backup format can be restored.

## Local development

Requires Node.js 22.13+ and npm. Development, builds, fixture tests and device/manual workflows require no API key, account, local database initialization or invitation. Real hosted inference requires a visitor-supplied key.

```sh
npm ci
npm run dev
```

Open `http://localhost:5173/workspace`.

```sh
npm test
npx tsc --noEmit
npm run lint
npm run build
node scripts/preview-built.mjs
```

In another terminal, run `node scripts/verify-browser.mjs`. It uses installed Microsoft Edge by default; set `DOVE_TEST_CHANNEL=chrome` for Chrome, or install Edge/Chrome first. The test accepts only localhost, creates an isolated browser profile and uses fictional data. It checks storage, quote/revision validation, PDF creation/extraction, package review/download, complete backup restoration and the absence of workspace API/authentication requests. Model inference is a separate hardware-dependent check.

To test actual model downloads and generation, run `node scripts/verify-model.mjs` against that same compiled preview with installed Chrome and a real WebGPU adapter. It downloads both offered models, creates fictional work through the interface, uploads a TXT source, checks generated quotes and human review requirements, and verifies download and analysis cancellation. Allow several GB of model downloads and enough free graphics memory. This manual check is separate from CI's proposal fixtures.

## Hosting and legacy data

`.openai/hosting.json` identifies the existing deployment. Preserve its project ID when updating this site. The host serves the application; users do not need a ChatGPT account. No server-side API key is required. Optional hosted analysis uses the visitor key supplied per request to `POST /api/analyze/visitor`.

Earlier authenticated D1/R2 workspace records and access requests are **not deleted, exposed publicly or automatically imported** by this release. Old workspace/access API routes return HTTP 410. Existing database migrations and resource bindings are retained to avoid destructive resource changes. Legacy records require a separate owner-controlled export; the old records-only JSON export is not a complete browser backup.

The Python/PostgreSQL application in the parent repository is a separate legacy implementation with its own authentication and optional providers. These browser changes do not convert that application.

## Verification

The October 2 hosted development check used real GPT-5.4 responses for five fictional PDF/TXT scenarios, including missing documents, conflicting records, unrelated-project acceptance and a longer source set. Expected category/status and quote checks passed after instruction refinement. Manual review still found an omitted invoice-date/due-date checklist item in the long example. GPT-5.4 mini was checked on the conflicting-record scenario only. These runs do not establish general accuracy or completeness; see [the recorded scope and limitations](../docs/HOSTED-WORKSPACE.md#verification).

The hosted adapter tests use injected provider responses to check request boundaries, exact source quotes, rejected statuses, cancellation and sanitized errors. They do not establish real hosted model quality; live inference must be checked separately.

September 30, 2026: 23 local browser checks passed using fictional documents, including no-login entry, local persistence, exact source checking, stale-write protection, PDF extraction, ZIP download, backup restore and separate browser-profile isolation. No workspace API or authentication requests occurred in that test. TypeScript, lint and production build checks are recorded with the release; one existing screenshot optimization warning is non-blocking. Real model quality and hardware support are not established by fixture tests.

October 2, 2026 UTC: both offered Qwen models downloaded and generated proposals using actual WebGPU in Chrome 154.0.8037.95. Source quotes matched the uploaded fictional document; download cancellation permitted retry, and analysis cancellation preserved the prior checklist. The [measured report](docs/model-verification-2026-10-02.json) records the resulting proposals. Each model omitted other possible requirements in this example, so check omissions manually. This confirms a controlled workflow on one device, not completeness, accuracy across documents or support on other hardware. The Llama 1B option was removed after it exceeded the output limit on this short input. Thirty Python fixture tests also passed locally; no live email or Python provider call was made.
