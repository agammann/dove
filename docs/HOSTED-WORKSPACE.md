# Hosted Dove workspace

[Open Dove](https://dove-paperwork.alx21.chatgpt.site/workspace) · [Hosted source and setup](../sites/README.md) · [Back to the repository](../README.md)

Dove's invitation workspace is hosted on ChatGPT Sites and remains available when the developer's computer is off. The public website and workspace share the same address. ChatGPT sign-in identifies the user; a single-use invitation separately grants workspace membership.

## First use

1. Sign in and redeem the invitation provided by the operator.
2. Open Settings. Save the business name and billing details, then resume automation.
3. Create a work item and verify its billing contact.
4. Upload text-readable PDF/TXT sources, then select Analyze documents.
5. Review the exact source quotes and make the checklist decisions.
6. Assemble a simple invoice or attach an existing invoice PDF. Confirm the source-supported amount and include the supporting documents.
7. Review the actual PDF and ZIP, then approve the exact version.

Download the approved ZIP and deliver it through your existing business process. Outgoing email is not configured on the published site. Automatic incoming-email processing and scheduled reminders are not implemented in this hosted version.

## Two implementations

| Capability | Sites workspace | Python application |
| :--- | :--- | :--- |
| Hosting | Published on ChatGPT Sites | Run locally or deploy to a compatible host |
| Identity | Sign in with ChatGPT and workspace invitation | Application invitation/password accounts |
| Records/files | D1 and private R2 | PostgreSQL/SQLite and local object storage |
| AI | Live OpenAI, server secret | Local fixture by default; optional OpenAI adapter |
| PDF/TXT upload, evidence review, package approval | Implemented | Implemented |
| Invoice | Existing PDF or simple confirmed total | Reviewed invoice lines |
| Outgoing email | Implemented explicit send routes; service unconfigured/unverified | Local outbox by default; optional live provider |
| Incoming email and reminders | Manual document/reply handling; no automatic scheduler | Worker and provider-integration workflow; live email still unverified |
| Backup/restore | Record export and individual file downloads; full recovery workflow pending | Backup script and isolated restore verification |

The Python sample and Sites workspace do not share accounts, documents or access requests. The public interest form creates neither type of account.

## Operator access and data

The site operator creates a workspace using the [private CLI invitation workflow](../sites/README.md#production-operations). Use the customer's ChatGPT email to bind an invitation. All workspace members can read its files and make approval decisions; granular roles are not implemented.

Secrets belong in the hosting environment and ignored local environment files. The published source and deployment archive contain no API key. Never add a NEXT_PUBLIC_ prefix to provider secrets.

An analysis sends extracted document text to OpenAI. Source quotes are checked against stored pages, and the model cannot approve requirements, authorize contact or send invoices. Adding sources or editing decisions invalidates previous package approvals.

Deletion hides the work immediately and removes its stored objects, retrying cleanup on subsequent workspace visits when storage was temporarily unavailable. Export records and download required binaries before deleting.

## Verification, September 19, 2026

- The actual production Worker build passed 16 local HTTP checks with fictional data and live OpenAI calls.
- Verified anonymous denial, one-time invitation membership, cross-workspace work/file denial, upload bounds, exact source quotes, human review, amount and date checks, PDF extraction, ZIP contents/digest, stale approvals, exact approval and unconfigured-email denial.
- Fixed rejected-request body handling after observing dropped local proxy connections; the full checks then passed.
- TypeScript and production build passed. ESLint passed with one existing screenshot optimization warning.
- Full npm dependency audit reported zero known advisories after updates; schema generation confirmed no new changes were needed.
- Sites version 2 deployed successfully from source commit d8eee7a322c1060d33e6697dce93b9b1a4495680 with environment revision 2.
- Public home and health returned 200; anonymous workspace API and session requests returned 401. Browser ChatGPT authentication reached the invitation screen.
- The signed-in owner workspace then completed a hosted fictional workflow: upload, live OpenAI analysis with four source-linked proposals, review (including a purchase-order waiver), PDF/ZIP generation, download and exact-version approval. No email was sent. The downloaded invoice PDF was rendered and inspected, and the ZIP manifest and source attachment were checked.
- Hosted fictional package DV-FF5DD5DC-1 was USD 24.00. Its downloaded ZIP matched the on-screen SHA-256 fingerprint: `6c8b8a9ac1daec2bb7895bfc339a5c6b2feb170464262f17af86dbc34c2e28f7`.
- GitHub's published Sites source was read back and matched the local source. All 50 repository-local Markdown link targets existed. Existing third-party design/reference links were not all rechecked in this release.

These are engineering checks using fictional documents. They are not real-customer usability results, a load test, a hosted disaster-recovery drill or proof of real email delivery.
