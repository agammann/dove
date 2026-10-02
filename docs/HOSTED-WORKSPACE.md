# Dove browser workspace

[Open Dove](https://dove-paperwork.alx21.chatgpt.site/workspace) · [Source and setup](../sites/README.md) · [Repository](../README.md)

Dove opens without a login, ChatGPT account or invitation. Device analysis and manual review need no paid AI API. Workspace records and uploaded files are saved in the visitor’s browser. Optional hosted analysis sends extracted text to OpenAI using the visitor’s own key and billing account.

## First use

1. Open the workspace and enter business/billing details in Settings.
2. Create a work item and verify its customer billing contact. The email field identifies the invoice recipient, not an account.
3. Add readable PDF/TXT sources. Choose device analysis, optional OpenAI analysis with your own API key, or enter source-linked requirements manually.
4. Review source quotes and make checklist decisions. Save request drafts for your own email and record replies you have verified.
5. Assemble an invoice and supporting package using a source-supported total.
6. Download and inspect the actual PDF and ZIP, then approve the exact version.
7. Deliver through your own process and export a complete backup from Settings.

## What changed

| Capability | Published browser workspace | Separate Python application |
| :--- | :--- | :--- |
| Accounts | None | Invitation/password accounts |
| Records/files | IndexedDB in the current browser profile | PostgreSQL/SQLite and object storage |
| Model | Browser WebGPU model or optional OpenAI with the visitor’s key | Fixture adapter by default; optional provider adapter |
| Evidence review and package approval | Local, human decisions | Server-backed, human decisions |
| Email | Save drafts and download packages; send through your own email | Local outbox by default; optional live provider |
| Backup | Complete ZIP export/import in Settings | Operator backup and isolated restore scripts |
| Collaboration | No shared workspace or automatic sync | Organization membership |

## Protect saved work

Clearing site data, using private browsing, changing profiles or browser storage eviction can remove local records. Anyone with access to that browser profile can open them. Dove does not encrypt records or backup ZIPs. Keep backups in a private location outside browser storage.

**Export complete backup** includes originals, extracted text, decisions, invoices and package ZIPs. **Restore backup** validates the file index and hashes before replacing the local workspace. Export current work first. Restored packages require renewed approval. Backups are not authenticated audit records.

Device analysis downloads model assets from public hosts on first use and requires WebGPU and sufficient graphics memory. Document text is processed locally in this mode; hosting and asset hosts may process ordinary request metadata. It never switches to paid analysis automatically.

Optional OpenAI analysis defaults to GPT-5.4 and is billed to the visitor’s account. The complete extracted text and filenames, plus the work title, customer and description, pass through the Dove server to OpenAI in one paid request. Hosted analysis accepts up to 32,000 extracted characters across all documents and proposes up to 20 requirements with one or two quotes each. Larger work is rejected before the request, without truncation; use device analysis or manual review. Requests use `store: false`; provider data policies still apply. The key stays in tab memory, is excluded from workspace backups, and can be cleared with **Clear key**, switching to device mode or reloading. Source words must match the cited document and page, with whitespace normalized in hosted quotes. Revision checks and human approval still apply. Check every proposal and any missing requirements yourself. Read [limits and development instructions](../sites/README.md).

## Legacy hosted data

The browser release retains the old D1/R2 resources and migrations. It does not publish, delete or automatically copy earlier hosted records. Old workspace and access-request routes are retired with HTTP 410. Recovery of legacy records requires a separate owner-controlled export, not a public endpoint or an unverified email claim. Old records-only JSON exports cannot restore original binaries and are not accepted as complete browser backups.

## Verification

October 2, 2026 UTC: five fictional PDF/TXT document scenarios completed through the compiled Worker and rendered browser interface using real GPT-5.4 responses. They covered matching records, missing PO/acceptance documents, conflicting amounts and acceptance, unrelated-project acceptance, and a 9,303-character source set. The final run matched 17 preset category/status targets; document/page/quote checks passed, and manual review of all 29 proposals confirmed the core conclusions. GPT-5.4 mini also completed the conflicting-record scenario with the expected amount and acceptance conflicts.

An earlier run omitted a payment term and a delivery requirement and inferred an invoice-format rule from a known billing contact. The instructions were refined using those same scenarios, so this is a development check, not a held-out accuracy benchmark. The final long example still omitted the invoice date and due date from its checklist. Review every source and add missing requirements; matching quotes and expected categories do not establish completeness or truth. The 32,000-character limit is an input bound, not a measured quality guarantee.

Hosted transport testing caught and fixed two integration failures: the Worker runtime rejects `redirect: error`, and strict provider schemas rejected multiline quote enums. The route now rejects manually handled redirects, and hosted quote options normalize source whitespace. Thirteen deterministic tests cover input limits, complete-document requests, quote attribution, redirect handling, cancellation and failure boundaries. The existing 23 browser storage/package/backup checks also passed separately from real inference.

A further real-response walkthrough verified cancellation and immediate retry, a real invalid-key response, key clearing on device-mode changes and reload, and credential-free browser storage and decompressed backups. All six requirements were reviewed against the source pages; five retained both citations through review. The downloaded invoice and ZIP were inspected for the total, recipient, dates, original attachment bytes and package fingerprint. Approval applied to that exact package and was invalidated by a new source. Native WebMCP changed the landing page illustration without initiating analysis. This check also exposed a 320-pixel layout issue, fixed by wrapping requirement headers and showing workflow tabs in two rows.

September 30, 2026: 23 local browser checks passed, covering no-login entry, durable local storage, source/revision checks, invoice PDF extraction, package approval, ZIP download, complete backup restoration, invalid-backup rollback and isolation between browser profiles. The workflow made no workspace API or authentication requests. Real model generation is checked separately from these fictional proposal fixtures.

October 2, 2026 UTC: the Qwen 3 1.7B and default Qwen 3 4B options completed real downloads and source-linked analysis in Chrome 154.0.8037.95 with WebGPU. Cancelled analysis preserved the existing checklist. Both models omitted other possible requirements in the controlled example; review missing items yourself. See the [model report](../sites/docs/model-verification-2026-10-02.json) and [repeatable hardware check](../sites/README.md#local-development).
