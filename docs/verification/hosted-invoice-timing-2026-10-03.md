# Hosted invoice timing and manual review — October 3, 2026

[Back to Dove](../../README.md) · [Earlier browser verification](../HOSTED-WORKSPACE.md#verification)

This record keeps three separate development checks: the original four first responses met 15 of 16 frozen criteria; a later five-case check retained one misleading-title failure; and two first responses after the title correction met their targeted criteria. No retries or later normalization turn an earlier failure into a pass. These are fictional development fixtures, not a held-out accuracy benchmark or completeness guarantee.

The original four cases below ran through the rendered workspace and compiled local Worker on October 3, 2026 UTC. Each made one real `gpt-5.4` request and returned HTTP 200. **Three cases fully met their frozen criteria; one remained incomplete.**

## Environment and source

- Windows, Microsoft Edge 154.0.4258.48 with browser sandboxing enabled, Playwright 1.62.1, Vinext 1.0.0-beta.10 and Wrangler 4.146.0.
- Explicit visitor-key mode, `gpt-5.4`, medium reasoning and `store: false`. Requests included complete extracted PDF/TXT pages and work context within the 32,000-character limit; context was not quoted evidence.
- The tracked browser source for the manual UI check is exactly the [`sites/` directory at published commit `b5e91432139ba79bf43eaa5d0d2175a34a165d99`](https://github.com/agammann/dove/tree/b5e91432139ba79bf43eaa5d0d2175a34a165d99/sites). The [source projection manifest](sources/invoice-timing-2026-10-03/source-projection.json) records all 128 tracked files and their hashes.
- The paid first-response source is the same published directory with the [reverse attribute patch](sources/invoice-timing-2026-10-03/paid-runtime-from-published.patch) removing `aria-label="Your decision"` from the decision selector. All other 127 tracked files match. The [historical analysis contract](https://github.com/agammann/dove/blob/b5e91432139ba79bf43eaa5d0d2175a34a165d99/sites/lib/analysis-contract.mjs) stayed byte-identical, SHA-256 `9ef477bafa322beaf518395c4e1bd02389de4fdc4310bcc21549f117345dc7df`. This projection reproduces tracked browser source, not private fixtures or compiled output. The manual UI check added no inference.

The model responses and 44-check manual run below used local compiled builds; the later production smoke is recorded separately.

## First-response findings

Criteria were frozen before the requests. All 28 proposals were reviewed against complete sources. Twenty-eight automated source/state checks passed, covering quotations, human-review state, no package creation and credential absence from saved work and local/session storage. All 46 quotations matched their cited pages after whitespace normalization. These checks alone do not establish semantic correctness.

| Case | Complete extracted characters | Proposals | Frozen criteria | Observed result |
| :--- | ---: | ---: | :--- | :--- |
| Long agreement and conflicting invoice | 9,303 | 6 | 4 of 4 met | A separate item states October 2/November 1 without inventing an agreed term. The USD 2,400/2,800 conflict and missing actual PO remain correctly identified. |
| Matching agreement, PO, acceptance and invoice | 1,699 | 7 | 4 of 4 met | Printed dates align with the explicit 30-day term, citing invoice and agreement page 2. Prior received-document conclusions remain supported. |
| Invoice due date inconsistent with the agreement | 1,699 | 8 | 3 of 4 met | Correctly flags October 25 against the 30-day term, citing both documents. It omits **November 1**, implied by October 2 plus 30 days, which the frozen explanation criterion required. |
| Invoice dates absent | 1,710 | 7 | 4 of 4 met | Both dates are flagged as missing while the agreement's 30-day term remains received information. No calendar date or contractual invoice-format rule is invented. |

Fifteen of sixteen criteria were met; this is a fixture result, not a model accuracy score. The inconsistent-date case also correctly noted that an undated acceptance record cannot prove the agreement's required acceptance-before-billing timing.

No unsupported factual reason was identified. Some titles in that run used affirmative conditions such as “aligns” beside `conflict`. Its omitted November 1 explanation remains an incomplete first response; the later changed-source checks below are separate evidence.

The long-document invoice-date omission improved here. Earlier payment-term/delivery omissions, an inferred invoice-format rule, device-model omissions and provider integration failures remain in the [October 2 history](../HOSTED-WORKSPACE.md#verification). This follow-up does not erase them.

## Separate manual-review UI check

A fresh context created a fictional work item, uploaded TXT and added two source-linked requirements through the interface. No model, key or hosted mode was used.

Forty-four checks passed, including:

- The decision selector exposed the exact accessible name “Your decision”; keyboard selection and manual saving worked, preserving source quotations.
- Unreviewed and partially reviewed items withheld readiness. After explicit test-only waivers, the interface displayed: “Every recorded checklist item is reviewed. Check the source documents for omissions before assembling the billing package.”
- The reminder, edit form and readiness state rendered at 1440 and 390 pixels without horizontal overflow. Saved decisions and readiness survived reload.
- No page errors, console warnings, external browser requests or HTTP writes occurred. No package or outreach draft was created; owned browser and server processes were closed afterward.

Local TypeScript, targeted lint, the production build and diff whitespace checks passed. The 44-check manual run did not repeat device inference, native WebMCP, package export or approval testing; their earlier dated evidence retains its original scope.

## Production manual workflow

On October 3 at 04:09 UTC, [the public workspace](https://dove-paperwork.alx21.chatgpt.site/workspace), version 8 with source `849ba4dee214f10982926bebfe4a08451d2c6ff4`, passed 47 checks in a fresh sandboxed Chrome 154.0.8037.98 context. The actual interface imported fictional TXT, added two source-linked requirements, saved keyboard/manual decisions, enforced unreviewed and partial-review blockers, and preserved readiness after reload. The reminder, decision form and readiness state rendered at 1440 and 390 pixels without horizontal overflow. No key, hosted mode, inference, package or outreach action was used.

The first production attempt passed 42 checks, then failed its 43rd check because an all-writes guard blocked two Cloudflare JavaScript Detection POSTs; both blocked-request console errors remain recorded. A separately reviewed follow-up allowed only the observed same-origin `/cdn-cgi/challenge-platform/h/b/jsd/oneshot/` POST prefix, capped at one per initial load/reload and two overall. It observed one initial request completing with HTTP 200 and none on reload. This is request-completion evidence, not a human/bot-clearance claim. No application API calls, other writes, external requests, WebSockets, page errors or console warnings occurred; the owned browser closed afterward.

All 20 observed asset responses, covering 10 distinct client paths, matched the submitted build manifest. This checks those served assets, not all build files or saved server-archive byte equality. The model-free production result does not change the incomplete semantic criterion above.

## Dependency audit history

The [October 3 PR CI run](https://github.com/agammann/dove/actions/runs/37093371712) passed the Python sample job but stopped the browser job at `npm audit --audit-level=low`, before its tests and build. The audit reported eight high-severity dependency entries for [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm): `braces` 3.0.3 and its transitive lint/build dependents, all marked development dependencies in the lockfile. The advisory listed no patched version when checked on October 3. This establishes an unresolved dependency finding, not a demonstrated exploit of the deployed app.

The entries are `braces`, `micromatch`, `fast-glob`, `@next/eslint-plugin-next`, `eslint-config-next`, `vite-plugin-dynamic-import`, `vite-plugin-commonjs` and `vinext`.

In those revisions, CI retained the full audit JSON and ran the remaining checks before a final audit gate. The job still failed unless the audit succeeded; its severity threshold and dependencies were unchanged. No clean dependency audit or fully green CI is claimed for those revisions.

The [follow-up CI run](https://github.com/agammann/dove/actions/runs/37094572964), at `b4531891f096c5f23e1757c70719a17be0981e5e`, passed the Python sample, browser unit tests, TypeScript, lint, build and 23 compiled-browser workflow checks with no browser errors or API transmissions. The overall run still failed its final audit gate on the same eight findings.

The later [build-migration record](browser-build-migration-2026-10-03.md) tracks removal of the affected build/lint dependency chains. [CI run 37107146490](https://github.com/agammann/dove/actions/runs/37107146490), at `99b258e4af5a6b10358d278c42b6246c3b0f8a24`, passed both jobs with zero audit findings. That later result does not change any model result above or relabel the earlier failed runs.

## Review-contract follow-up

Source review found that the two-citation limit could not represent a payment term, invoice date and due date on three separate pages. It also showed that a genuine but unrelated quote does not establish a missing-date claim. Deterministic regressions exercise those boundaries separately from the model checks below.

Hosted results now permit one to three citations and must declare a scope covering every supplied extracted page. Missing-information titles and explanations describe what the model did not identify and require human review of the complete originals. A document’s invoice role remains model-identified. This validates source membership and declared coverage, not absence or understanding. Assembly and exact-package approval both repeat the requirement to check source omissions, invoice dates and agreed payment terms. Storage/backup formats and device mode are unchanged.

### Five first responses before the title correction

At 10:27–10:30 UTC, five fictional cases used the rendered workspace and compiled Vite/Cloudflare Worker with Edge 154.0.4258.48, Playwright 1.62.1 and Wrangler 4.146.0. Each made one real `gpt-5.4` request, reported model `gpt-5.4-2026-03-05`, and returned HTTP 200 without retries. Complete source, medium reasoning, `store: false` and the visitor-supplied-key boundary remained in force.

All 32 raw and saved proposals were reviewed against the complete sources; 64 quote references and 40 automated source/state checks passed. Four cases were supported: long conflicting records, matching records, inconsistent invoice dates and missing invoice dates. The three-page case retained the correct three citations and explained November 1 versus October 25, but its title said **“Printed due date matches the 30-day payment term”** while status was `conflict`. That contradictory title makes this first response a semantic failure. Correct quotations and the explanation do not rescue it.

### Two first responses after the title correction

The hosted instructions now request neutral review-action or requirement titles. Newly normalized hosted conflicts receive a fixed neutral title for their category; custom conflicts use **“Review conflicting source information”**. The model’s reason, status and all references are retained. Existing saved/imported requirements and human-edited titles are not rewritten; this is not a semantic correction of arbitrary explanations.

At 11:05–11:07 UTC, two new first requests used that changed compiled source and the same model/environment. Both returned HTTP 200 without retries. Independent review covered all 14 raw and saved proposals, eight unique complete source pages and 31 quote references; both cases met their frozen raw and saved criteria. Sixteen source/state checks passed separately.

| Case | Observed result |
| :--- | :--- |
| Inconsistent-date TXT invoice | A neutral raw timing title and explicit explanation distinguish invoice date October 2, the agreed 30-day term, implied November 1 and printed October 25. Agreement and invoice citations support the conflict. |
| Three-page PDF invoice | The same comparison retains agreement page 2, invoice page 1 and invoice page 2 in one conflict. Page 3 is included and supports the PO reference; no missing date is invented. |

The remaining PO, delivery, acceptance, USD 2,400 and authorized-recipient conclusions were supported. Both saved conflicts used the fixed neutral title without altering reasons, statuses or references. No missing-information claims occurred in these two responses, so they add no absence-detection evidence. Six recorded Review views at 1440/390/320 pixels were inspected; these show the upper Review area, not editing of the later citation cards. No errors or disallowed requests were recorded, and owned processes closed.

The [complete source projection](sources/invoice-timing-2026-10-03/source-projection.json) includes all 138 browser-source files for both later revisions and reconstruction patches from published commit `36cf550700e42f6a2d2c779520523256cd9b25c7`. It preserves the earlier four-case projection too. This is inspectable tracked source, not private fixtures or compiled output.

### Separate Package and backup UI checks

At 10:17 UTC, a model-free compiled-client run passed 86 checks in Edge 154.0.4258.48. It created fictional manual decisions, verified omission reminders on direct Package entry after reload and restore, blocked unchecked assembly and approval, and downloaded the actual invoice PDF, package ZIP and complete backup. File hashes, invoice fields and package digest were checked. Fresh-context restoration reset approval; a new source invalidated the old package. A retained historical format-1 backup also restored without a schema change. The earlier browser-launch and field-selector attempts remain failed preparation history, not application passes.

That UI run used the pre-title-correction revision. Workspace UI, storage, backup and package code are byte-identical between the two later model revisions; only the hosted prompt/title normalization and its tests changed. No model inference occurred in the Package/backup check.

At 11:29 UTC, a separate model-free run imported the actual two-work backup from the successful model follow-up and passed 14 checks. All three references rendered; a manual reason-only edit kept the conflict unresolved and retained the exact citation document IDs, pages and quotations. Reload, one backup export and a fresh-context restore preserved the edited work/workspace records and all eight original source-file bytes. The complete citation card was inspected at 1440 and 390 pixels. No inference, key, approval, package or outreach action occurred. The storage concurrency counter changed normally on saving and fresh restoration; the backup format remained version 1.

The final local title-correction source passed 25 unit tests, TypeScript, zero-warning lint and the compiled build. The published revision and its subsequent checks are recorded below. The earlier four-case 15/16 result and five-case title failure remain unchanged.

## Published follow-up

[PR 4](https://github.com/agammann/dove/pull/4) merged the reviewed changes. [Final CI run 37121576467](https://github.com/agammann/dove/actions/runs/37121576467) passed 25 unit tests, 23 compiled-browser checks, TypeScript, lint, build and the required dependency-audit gate. The separate Python sample passed 30 SQLite and 30 PostgreSQL tests; Docker health, the non-root command and backup/isolated restore checks passed. Existing non-failing dependency, chunk-size and Python deprecation warnings remain.

At 12:48 UTC on October 3, [Dove v11](https://dove-paperwork.alx21.chatgpt.site/workspace/) was published from Site source `e9a41a252e57972ab1010c9d7b7b834534a4697a`. All 20 subsequent bounded public HTTP checks passed: canonical routes, redirects without following them, expected unknown/configuration 404s and the observed HTML/assets. The harmless 24-byte `.assetsignore` is publicly served; its earlier incorrect 404 expectation remains a recorded failed check.

At 13:06 UTC, one first production `gpt-5.4` submission, without retries, passed 15 transport/source/UI checks. Independent review of all seven complete source sections found all six raw and saved proposals and 14 quotations supported. The three-citation conflict distinguishes the October 2 invoice date, the agreement's 30-day term, the implied November 1 date and the printed October 25 due date. It remains unresolved and requires a human decision. The key was cleared before screenshots and a genuine 19,003-byte backup export containing the saved work and four original files.

This adds one fictional public-handler case, not general accuracy, completeness, absence-detection or full-limit coverage. The retained response is the actual validated handler body before client normalization; the internal raw provider envelope is unavailable. Earlier native WebMCP checks retain their recorded revision and browser scope; no new final-v11 native run is claimed. This fresh profile also does not establish existing visitors' public-origin storage continuity. All earlier failures remain unchanged.

## What an operator still needs to do

Compare invoice dates with agreed terms and check original documents for missing items. `received` means source information is present, not verified or approved. Review every recorded item and any source omissions before assembling and approving an exact billing package.
