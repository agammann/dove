# Browser build migration — October 3, 2026

[Browser setup](../../sites/README.md#local-development) · [Invoice-timing results](hosted-invoice-timing-2026-10-03.md)

The browser application uses React and Vite with a Cloudflare Worker. The landing page and initial workspace view are pre-rendered, then hydrated. Explicit Worker routes preserve `/` and `/workspace`, slash redirects, retired workspace/access APIs, the visitor-key handler and asset 404 responses. Managed hosting behavior remains a separate deployment check.

The migration removes the Next lint configuration and Vinext build chains that pulled in `braces`. Direct ESLint configuration retains the React, hooks/compiler, TypeScript, accessibility and import rules. The audit threshold remains `low`, with no advisory waiver. The locked dependency audit reported zero findings on October 3 at 06:32 UTC. Earlier failed audit runs remain recorded in [the invoice-timing history](hosted-invoice-timing-2026-10-03.md#dependency-audit-history).

## Recorded checks and limits

The local locked installation, 19 unit tests, TypeScript, lint and production build passed. The earlier migration build passed the existing 23 browser storage, document, invoice, package and backup checks. The paid-analysis handler, analysis contract, storage and backup implementation are unchanged; these source comparisons are separate from rendered and provider testing.

Wider browser testing exposed a strict test-label lookup problem after reloading a populated billing textarea and a clipped landing heading at 320 pixels. The browser test now targets the uniquely named billing field while retaining exact saved-value and associated-label checks; narrow stylesheet changes address the heading and keep the mobile illustration caption below its front card. An intermediate run failed on response-body capture after navigation and a fixture initialization error; those failed outcomes remain recorded.

On October 3 at 07:26 UTC, the final compiled local preview passed **137 checks** in fresh sandboxed Edge 154.0.4258.48 contexts. These covered explicit HTTP routes and methods, all 11 public client files against the compiled bytes, pre-rendered metadata and no-JavaScript landing behavior, actual hydration/navigation, exact settings persistence after reload, separate-profile isolation, and landing/workspace/settings layouts at 1440, 390 and 320 pixels. One missing-key request returned 401 before provider invocation. All 66 observed browser asset responses matched their pinned files; no page errors, console warnings or disallowed browser requests occurred, and the owned browser closed. The mobile screenshots and text bounds confirmed the headings fit and the caption no longer overlaps the front card.

The injected browser-agent lifecycle checks in that run are fixtures; genuine native evidence is recorded separately below. Managed production migration checks remain separate from this local result.

## Local saved-state upgrade

At 07:33 UTC, one fictional approved workspace passed a same-origin transition from the pre-migration compiled build based on `80ed120` to the final migration candidate in Edge 154.0.4258.48. A local proxy switched the served build while retaining the same browser profile and origin; no backup export/import was used. Settings, work creation and TXT upload used the old interface. A source-linked manual requirement and generated package were prepared through the old local libraries, then approval and downloads used the actual interface. No model or provider was involved.

All three verification groups passed. The complete saved state and three stored files were unchanged, including the exact package approval. The new interface retained the settings and downloaded the original TXT, invoice PDF and package ZIP with matching stored hashes; the invoice downloaded before and after the transition was byte-identical. No API/authentication/model requests, browser errors or network violations occurred, and owned processes and ports closed afterward. Earlier path-preflight and Currency-selector attempts remain recorded as failed; they passed no acceptance groups.

This checks one local fixture across the two compiled builds, not continuity for an existing visitor on the public origin. Public deployment continuity and new exact-head CI remain unverified at this point.

## Genuine native WebMCP

On October 3 at 07:11 UTC, the compiled local preview passed 36 checks in a fresh Chrome **154.0.8037.98** context with **`--enable-features=WebMCPTesting`**. The real `document.modelContext.getTools()` and `executeTool()` APIs discovered the landing tool and executed Gather, Resolve and Approve. Returned step/label values matched the selected tabs and rendered headings. Six invalid calls, including an extra property, were rejected without changing the visible step. The tool list was empty on the workspace and contained one tool again after returning to the landing page.

The first native run accepted an extra property despite the declared schema. The callback now validates the exact object shape before changing the illustrative step. In the successful run, six console messages from the intentionally rejected callbacks were recorded separately; there were no unexpected errors, warnings or API, authentication, external, write or WebSocket requests. This establishes this browser build and testing-flag configuration, not production deployment, third-party agent integration, BFCache behavior or general browser compatibility. The native run preceded the final mobile caption CSS change; the callback and validation code did not change afterward.

No new model inference was performed for this migration. The four earlier first GPT-5.4 responses still met 15 of 16 frozen semantic criteria, with the implied November 1 date missing from one explanation. Device-model omissions and earlier provider failures retain their dated scope. Visitor-key mode remains explicit, uses the visitor's billing account and fixed provider endpoint, excludes keys from saved work and backups, and requires manual source review.
