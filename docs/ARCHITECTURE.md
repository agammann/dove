# Dove architecture

Dove runs one configurable paperwork workflow for every business type. The React application is served by FastAPI on the same origin. PostgreSQL stores organization-scoped records, jobs, invitations, sessions and immutable package metadata. A separate Python worker polls durable jobs. Private document objects use opaque keys on a persistent volume outside the web root; they are never served as static files. Five-minute download tokens also require the same authenticated user and organization.

## Domain records

`organizations`, `users`, `sessions`, and `invitations` are explicit tables. `records` is an indexed, organization-scoped domain store with a `kind`, work identifier, unique deduplication key, timestamp and JSON payload. Kinds include customer, contact, work, document version, requirement, evidence, request, incoming message, decision, package version, delivery attempt, job, activity, usage and webhook receipt. Pydantic validates incoming commands and model output. This compact beta model favors one common transactional workflow over a table for every payload. Schema changes still require a migration and compatibility review.

Every private lookup resolves organization and record identity together. Child references are checked against the organization and work item. The worker derives organization scope from persisted jobs, never model output. The only global routing lookup matches a signed provider event to an existing opaque reply address or provider message identifier. Unmatched signed events enter a restricted operations queue; they do not enter a customer workspace.

## Authentication

Invitation-only account creation uses random expiring invitation tokens stored as SHA-256 hashes and single-use database updates. Passwords use the maintained pwdlib Argon2 implementation. Random session tokens are stored hashed, expire after 12 hours, and use HttpOnly, SameSite=Strict cookies (Secure in production). Same-origin write checks and an explicit action header protect against cross-site writes. Persistent login counters limit attempts by source IP and account. Public beta currently has one operator permission level per organization. CLI access is the deployment operator boundary for issuing invitations and reviewing access requests.

## Workflow and approval boundaries

Upload validates PDF/TXT content and processing bounds, stores a new object and creates an analysis job. Exact document IDs, versions, pages, excerpts and values from model output are validated against the extracted text. No model gets email credentials or application mutation tools. Local rules produce the same validated proposal schema, with a simulated label.

Requirements are independently missing, received, needs review, satisfied or internally waived. The operator reviews them and confirms the checklist. A request additionally requires an authorized customer contact, explicit follow-up permission, currently missing requirements, unpaused automation and available allowance. Reminders default to two at least two business days apart in the configured IANA timezone (weekends excluded; public holidays are not modeled).

Incoming provider events are authenticated with Svix signatures over raw request bytes. An incoming record and durable hydration job commit before the webhook acknowledges. Reply routing never uses subject alone. Replies are evidence proposals: they cannot establish approval authority. Every substantive reply creates a human decision. Forwarded/unknown-sender messages are flagged; out-of-office messages do not resolve requirements. Attachments are explicitly retrieved through a size-bounded, allowlisted provider endpoint and the normal PDF/TXT validation path.

Generated invoice totals use Decimal and round line amounts half-up to two places. Supported currencies currently have two decimal places. Each generated charge must match reviewed amount evidence in the work item's currency. Invoice numbers increment under the organization lock. Existing PDF invoice bytes are preserved. The manifest binds business/customer details, dates, currency, amounts, recipients and supporting document IDs/versions/hashes. ZIP bytes are written once, hashed and never overwritten. Approval records bind the ZIP digest and work revision; delivery authorization is a separate command. Changes invalidate pending approval. A later correction builds a new package.

## Concurrency and recovery

PDF processing runs in child processes with a 15 second timeout, at most two active children per process and one per organization. Linux children additionally enforce 512 MiB address space and 10 seconds CPU. Child environments exclude provider credentials. Upload parsing happens before the organization mutation transaction.

Storage counts physical retained objects, including orphaned files awaiting cleanup. Defaults are 512 MiB and 1000 objects per organization, 100 document versions and 20 package versions per work, and 20 MiB per package. Durable garbage collection deletes files after database commit. Requests, packages and manual retries share the same outgoing allowance reservation under the organization lock.

OpenAI also proposes editable request text and grounded reply associations. Drafting reserves a model call before inference and never authorizes sending. Replies still create a human decision if inference fails or the allowance is exhausted. No inferred association satisfies a requirement without review.

All organization mutations take a PostgreSQL organization-row lock. SQLite local mode uses BEGIN IMMEDIATE and is not the deployment database. This intentionally serializes beta organizations; it trades throughput for auditability. Jobs have due times, leases, attempt counts and visible errors. Normal processing retries at most three times with backoff; manual retries remain subject to model limits. A model call allowance is reserved before inference, even if the inference later fails.

Email sending first commits an attempt in `sending`, then calls the provider once with an idempotency key. A crashed/expired sending intent becomes `uncertain`. An unknown response never automatically repeats the external action. Known IDs can be reconciled against Resend; no-ID uncertainty requires provider investigation. Definite rejections can be manually retried at most three times. Provider acceptance, delivery events, bounces, failure, customer acceptance and payment are separate concepts.

## Deliberate limits

- One API and one worker are the supported deployment shape initially; concurrency tests also exercise competing workers.
- Model calls serialize within each organization during analysis. No agent framework or multi-agent workflow.
- Private volume-backed object adapter; distributed S3 storage is an extension point, not configured in this release.
- No OCR, full inbox sync, accounting ledger, payment processing, automatic tax decisions or native mobile app.
- HTML email is not rendered as active content. Unsupported attachments require a readable replacement.
- The model adapter's live accuracy and the provider-specific inbound/attachment behavior require an authorized integration test before beta.
