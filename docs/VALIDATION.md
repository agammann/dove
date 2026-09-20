# Dove validation

Updated September 19, 2026, Pacific time. These checks use fictional data. The public access website and the local document workspace are separate services.

## September 19 verification

| Check | Result | Boundary |
| :--- | :--- | :--- |
| Container SQLite suite | 30 passed, 1 warning, 39.86 seconds | Fixture model and local email |
| Container PostgreSQL suite | 30 passed, 1 warning, 22.89 seconds | Newly created disposable database, removed afterward |
| Running HTTP workflow | Passed sign-in, upload, worker processing, request, duplicate reply, human decision, approval, simulated delivery, ZIP download and export | Actual local API, PostgreSQL and independent worker; no live AI or email |
| Access separation | Foreign work returned 404; foreign signed file download returned 403 | Two fictional organizations |
| Browser | Sample sign-in, persisted checklist, package details and exact invoice preview rendered | Local app in Chromium |
| Database recovery fix | Added and inspected `restart: unless-stopped`; database and API healthy | Fixes absent restart policy; no Docker engine outage or host power-loss drill performed |
| Backup and isolated restore | Passed; six stored objects matched hashes, restored package ZIPs verified | Local backup; no restored worker started; not an off-host disaster recovery drill |
| Frontend build | TypeScript and Vite passed natively and in Docker; Docker used pnpm 10.16.1 | Vite 6.4.3, Playwright 1.55.1 |
| Dependency advisories | `pnpm audit` and hash-locked Python requirement audit reported no known vulnerabilities | Package databases at check time; does not audit container OS packages or certify security |
| Public website | Workflow navigation and access form passed; new fictional request confirmed in hosted D1 database | Records interest only, creates no workspace account and sends no automatic email |

The container test warning is a dependency deprecation of `anyio.abc.BlockingPortal` in Starlette's test client.

The running workflow produced fictional invoice DV-000002 for USD 2400.00. Package ZIP SHA-256: `2e3e2b43b392ca3a6f5a2dbd407f5b00850044b5f96427b1a08baf5626900315`. Its documents and delivery history remained available after the backup stop/start. All outbound attempts used the local outbox; none were sent to a real inbox.

Five frontend development-tool advisories were reported before patching. Updated Vite from 6.4.1 to 6.4.3 and Playwright from 1.55.0 to 1.55.1; the follow-up frontend audit returned zero known advisories. See the upstream [Vite advisory](https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff) and [Playwright advisory](https://github.com/advisories/GHSA-7mvr-c777-76hp).

Live OpenAI and Resend credentials were not configured. Live extraction quality, real send/reply/attachment/delivery behavior, public workspace hosting and real participant usability remain unverified. Follow [release gates](RELEASE-CHECKLIST.md) and the [pilot kit](PILOT-KIT.md) before real customer onboarding.

## Historical September 10 evidence

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

## Known limits

Live OpenAI extraction, drafting and reply interpretation remain unverified. Live Resend sending, inbound signatures, attachment retrieval, delivery events and uncertainty reconciliation need a configured domain and authorized test recipient. Fixtures cannot establish model accuracy or inbox interoperability.

One API and one worker on Linux are the supported initial deployment. PDF children have a 15 second timeout and admission control; Linux adds memory and CPU limits. Native Windows does not enforce the Linux process memory limit. Public holidays are not included in reminder business day calculations.

OCR, arbitrary file formats, full mailbox sync, accounting integrations, tax decisions, payment collection and granular organization roles are outside this release. Operators review invoice evidence, recipients and supporting document approval. Backups still require encrypted external storage, retention scheduling and a deletion ledger before real customer onboarding.
