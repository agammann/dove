# Dove validation

Observed September 10, 2026, Pacific time. These results concern local source and fictional examples.

## Observed evidence

| Check | Result | Boundary |
| :--- | :--- | :--- |
| Native Windows SQLite suite | 30 passed, 1 warning, 16.09 seconds | Fixture model and local email |
| Final Linux container PostgreSQL suite | 30 passed, 1 warning, 19.83 seconds | Dedicated disposable database |
| Linux container suite before final draft test | 29 passed, 1 warning, 38.64 seconds | Isolated SQLite database |
| TypeScript and Vite build | Passed | Does not prove live providers |
| Docker Compose | API healthy, PostgreSQL healthy, separate worker running | No public deployment |
| Browser workflow | Source review, authorized request, local reply, human decision, exact invoice preview, approval and simulated provider acceptance | Fictional design studio |
| Persistence | Sent work and delivery history remained after backup restart | Local PostgreSQL and objects |
| Backup restoration | Passed; four objects verified in isolated database; no restoration worker started | Document/package hashes verified; recovery duration not measured |
| Responsive inspection | Desktop 1360 by 900 and mobile 390 by 844 inspected; no mobile horizontal overflow | In app Chromium browser |

The fictional package was invoice DV-000001 for USD 2400.00. ZIP SHA-256: `6c53937987f19ecec344c33b9c578e4b7a33db0f34778085288bcfec681ce0d3`. Local provider ID: `local-package-c90b58cf-fa6c-411c-8b60-99273a9a3626`. This is simulated provider acceptance, not a real email, confirmed delivery, customer acceptance or payment.

Tests cover cross organization reads and mutations, approval invalidation, amount evidence, durable reply deduplication, uncertain sends, retry bounds, worker concurrency, exports, authentication, quotas, PDF admission and timeout, exact invoice preview, duplicate charge rejection and request drafting without send authority. The PDF blocking test uses a controlled delayed child process; it is not a production load test.

## Security review and remediation

Codex Security completed scan `09ef0b51-214b-464f-905f-2ae9cbaa93c5` against the original unversioned snapshot. The scan warned that files changed during scanning and saved results for the original snapshot. It reported three medium findings: PDF processing availability, unbounded retained file versions and inconsistent outgoing message allowances.

The changed source moves PDF processing into bounded subprocesses outside organization transactions, enforces physical storage and retained version limits, and shares outgoing reservations across requests, packages and retries. Regression tests exercise these changes. The historical scan findings are not automatically closed by local changes. Current source and deployment review remains a release gate.

The scan tool reported 7,317,325 total tokens across five threads, including 6,726,528 cached input tokens. This is aggregate tool reported usage with repeated context, not an estimate of incremental billing. The review excluded a full dependency advisory audit, live providers and production infrastructure.

## Known limits

Live OpenAI extraction, drafting and reply interpretation remain unverified. Live Resend sending, inbound signatures, attachment retrieval, delivery events and uncertainty reconciliation need a configured domain and authorized test recipient. Fixtures cannot establish model accuracy or inbox interoperability.

One API and one worker on Linux are the supported initial deployment. PDF children have a 15 second timeout and admission control; Linux adds memory and CPU limits. Native Windows does not enforce the Linux process memory limit. Public holidays are not included in reminder business day calculations.

OCR, arbitrary file formats, full mailbox sync, accounting integrations, tax decisions, payment collection and granular organization roles are outside this release. Operators review invoice evidence, recipients and supporting document approval. Backups still require encrypted external storage, retention scheduling and a deletion ledger before real customer onboarding.
