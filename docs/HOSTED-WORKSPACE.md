# Dove browser workspace

[Open Dove](https://dove-paperwork.alx21.chatgpt.site/workspace) · [Source and setup](../sites/README.md) · [Repository](../README.md)

Dove opens without a login, ChatGPT account, invitation or paid AI API. Hosting serves the website; the workspace and document processing run in the visitor’s browser.

## First use

1. Open the workspace and enter business/billing details in Settings.
2. Create a work item and verify its customer billing contact. The email field identifies the invoice recipient, not an account.
3. Add readable PDF/TXT sources. Analyze them using a local browser model or enter source-linked requirements manually.
4. Review source quotes and make checklist decisions. Save request drafts for your own email and record replies you have verified.
5. Assemble an invoice and supporting package using a source-supported total.
6. Download and inspect the actual PDF and ZIP, then approve the exact version.
7. Deliver through your own process and export a complete backup from Settings.

## What changed

| Capability | Published browser workspace | Separate Python application |
| :--- | :--- | :--- |
| Accounts | None | Invitation/password accounts |
| Records/files | IndexedDB in the current browser profile | PostgreSQL/SQLite and object storage |
| Model | Browser WebGPU model; no paid AI API | Fixture adapter by default; optional provider adapter |
| Evidence review and package approval | Local, human decisions | Server-backed, human decisions |
| Email | Save drafts and download packages; send through your own email | Local outbox by default; optional live provider |
| Backup | Complete ZIP export/import in Settings | Operator backup and isolated restore scripts |
| Collaboration | No shared workspace or automatic sync | Organization membership |

## Protect saved work

Clearing site data, using private browsing, changing profiles or browser storage eviction can remove local records. Anyone with access to that browser profile can open them. Dove does not encrypt records or backup ZIPs. Keep backups in a private location outside browser storage.

**Export complete backup** includes originals, extracted text, decisions, invoices and package ZIPs. **Restore backup** validates the file index and hashes before replacing the local workspace. Export current work first. Restored packages require renewed approval. Backups are not authenticated audit records.

First model use downloads assets from public hosts and requires WebGPU and sufficient graphics memory. There is no paid fallback. Document text is processed locally; hosting and asset hosts may process ordinary request metadata. Read [limits and development instructions](../sites/README.md).

## Legacy hosted data

The browser release retains the old D1/R2 resources and migrations. It does not publish, delete or automatically copy earlier hosted records. Old workspace and access-request routes are retired with HTTP 410. Recovery of legacy records requires a separate owner-controlled export, not a public endpoint or an unverified email claim. Old records-only JSON exports cannot restore original binaries and are not accepted as complete browser backups.

## Verification

September 30, 2026: 23 local browser checks passed, covering no-login entry, durable local storage, source/revision checks, invoice PDF extraction, package approval, ZIP download, complete backup restoration, invalid-backup rollback and isolation between browser profiles. The workflow made no workspace API or authentication requests. Real model generation is checked separately from these fictional proposal fixtures.

October 2, 2026 UTC: the Qwen 3 1.7B and default Qwen 3 4B options completed real downloads and source-linked analysis in Chrome 154.0.8037.95 with WebGPU. Cancelled analysis preserved the existing checklist. Both models omitted other possible requirements in the controlled example; review missing items yourself. See the [model report](../sites/docs/model-verification-2026-10-02.json) and [repeatable hardware check](../sites/README.md#local-development).
