# Hosted invoice timing and manual review — October 3, 2026

[Back to Dove](../../README.md) · [Earlier browser verification](../HOSTED-WORKSPACE.md#verification)

Four fictional cases ran through the rendered browser workspace and compiled local Worker on October 3, 2026 UTC. Each made one real `gpt-5.4` request and returned HTTP 200; first responses were retained without retries. **Three cases fully met their frozen criteria; one remained incomplete.** This is a development check, not a held-out accuracy benchmark or completeness guarantee.

## Environment and source

- Windows, Microsoft Edge 154.0.4258.48 with browser sandboxing enabled, Playwright 1.62.1, Vinext 1.0.0-beta.10 and Wrangler 4.146.0.
- Explicit visitor-key mode, `gpt-5.4`, medium reasoning and `store: false`. Requests included complete extracted PDF/TXT pages and work context within the 32,000-character limit; context was not quoted evidence.
- Real-response source tree: `a7056fe2fb534914cdd20cd9f4f3731ad6dead51`, based on `3827d0a7246b585f3cc9bef2ba5ad3ea57ca87ed`.
- Manual UI tree `8c461bb2e9e357611d34ee9fdba43324c7a4236e` added only an accessible label to the decision selector. The [analysis contract](../../sites/lib/analysis-contract.mjs) stayed byte-identical: SHA-256 `9ef477bafa322beaf518395c4e1bd02389de4fdc4310bcc21549f117345dc7df`. Model responses remain attributed to the earlier tree; the UI check added no inference.

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

No unsupported factual reason was identified. Some titles use affirmative conditions such as “aligns” beside `conflict`; read status, explanation and sources together. The omitted November 1 explanation remains unresolved.

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

## Dependency audit remains blocked

The [October 3 PR CI run](https://github.com/agammann/dove/actions/runs/37093371712) passed the Python sample job but stopped the browser job at `npm audit --audit-level=low`, before its tests and build. The audit reported eight high-severity dependency entries for [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm): `braces` 3.0.3 and its transitive lint/build dependents, all marked development dependencies in the lockfile. The advisory listed no patched version when checked on October 3. This establishes an unresolved dependency finding, not a demonstrated exploit of the deployed app.

The entries are `braces`, `micromatch`, `fast-glob`, `@next/eslint-plugin-next`, `eslint-config-next`, `vite-plugin-dynamic-import`, `vite-plugin-commonjs` and `vinext`.

CI now retains the full audit JSON and runs the remaining checks before a final audit gate. The job still fails unless the audit succeeds; the severity threshold and dependencies are unchanged. No clean dependency audit or fully green CI is claimed for this revision.

The [follow-up CI run](https://github.com/agammann/dove/actions/runs/37094572964), at `b4531891f096c5f23e1757c70719a17be0981e5e`, passed the Python sample, browser unit tests, TypeScript, lint, build and 23 compiled-browser workflow checks with no browser errors or API transmissions. The overall run still failed its final audit gate on the same eight findings.

## What an operator still needs to do

Compare invoice dates with agreed terms and check original documents for missing items. `received` means source information is present, not verified or approved. Review every recorded item and any source omissions before assembling and approving an exact billing package.
