# Data handling and retention

This is an implementation description, not a compliance certification or a promise of confidentiality beyond the configured deployment.

## Data and destinations

| Data | Stored in Dove | External recipient in live mode |
|---|---|---|
| Account emails, password hashes, session/invitation hashes | PostgreSQL | None from authentication code |
| Customers, contacts, work descriptions, requirements, decisions | PostgreSQL | Authorized request content goes to Resend |
| Uploaded PDF/TXT files and immutable billing packages | Private persistent object volume | Approved email attachments go to Resend and explicitly authorized recipients |
| Extracted document text | PostgreSQL | OpenAI for structured requirement proposals; `store=False` is requested |
| Incoming email text and attachment metadata | PostgreSQL | Originates with Resend; attachments retrieved on operator request |
| Missing requirement titles and work title | PostgreSQL | OpenAI for editable request drafting |
| Incoming reply text and candidate requirements | PostgreSQL | OpenAI for proposed associations; human review remains required |
| Access request form | Restricted operator records | No model submission; manual response only |
| Ordinary logs | Process logs | Hosting operator's configured log destination |

`store=False` does not by itself establish zero retention by OpenAI. Provider retention, abuse monitoring, subprocessors, geography and contractual terms must be reviewed before real customer data is onboarded. Resend handles addresses, message bodies and attachments needed for delivery and receiving. Provider accounts and DNS are not configured by the local build.

Local sample mode uses fictional `.example` addresses, deterministic extraction fixtures and a database outbox. Sample seed/reset refuses production mode or live adapters. Sample organizations are separate from real organizations. Do not use the shared sample password in production; the production runtime disallows fixture adapters.

## Operational policy for invitation beta

- Keep active work until the customer deletes it or the pilot ends. Review inactive records with each pilot customer after 90 days.
- Keep encrypted daily backups for 30 days, weekly backups for 8 weeks, then expire them. The longest backup retention is 56 days. Configure and verify expiration at the actual backup destination.
- On deletion, remove active records and files, cancel work jobs and reminders, and revoke sessions when deleting the organization. Already accepted email cannot be recalled.
- Record deletion requests separately at the operator level when needed to prevent a restored backup from reactivating deleted customer work. Apply that deletion ledger before restarting a restored worker.
- Remove resolved public access requests after 90 days; operator CLI review is restricted to the deployment owner. Public rate-limit buckets can be removed after 24 hours.
- Routine logs must not include document bodies, email payloads, passwords, tokens or request headers. The startup command disables HTTP access logs to avoid download-token leakage. Store actionable failures in the authenticated work item view.

Data export is available in Settings and contains work records plus source and package files. Treat exports as sensitive. Downloads require an active same-user session and expire after five minutes. Browser responses disable caching. File contents are never interpreted as application instructions.

## Before real customers

Choose the hosting region, enable encrypted backup storage, confirm backup expiration, inspect the provider contracts and account retention controls, define a support contact and privacy notice, test a real sender/recipient pair, and conduct a deployment access review. These are release steps, not completed claims.
