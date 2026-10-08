# Build on Dove

Start with the [browser quickstart](docs/BROWSER-QUICKSTART.md) and [browser development setup](sites/README.md#local-development). The browser app, separate Python example and legacy hosted resources have distinct data stores; preserve their boundaries.

For browser changes, enter `sites/`, install with `npm ci`, then run `npm test`, `npx tsc --noEmit`, `npm run lint` and `npm run build`. Start `node scripts/preview-built.mjs` and run `npm run test:browser` in another terminal. `node scripts/verify-native.mjs` checks the actual illustrative landing tool in Chrome 154/155. Model download/generation and live visitor-key checks are separate from injected provider fixtures.

Keep regression coverage focused on the changed behavior. Use fictional PDF/TXT sources, inspect the rendered interaction, and check desktop plus a narrow mobile viewport when changing the interface. Source references, stale-write checks, explicit human approval and complete recovery are part of the product contract.

For Python sample changes, follow [development](docs/DEVELOPMENT.md) and run its isolated SQLite/PostgreSQL tests and backup restoration. Never point a destructive fixture at an application database.

Exclude API keys, customer documents, databases, browser profiles, backup files and temporary reports from commits. Preserve lockfiles and third-party notices. Explain the observed problem, resulting behavior and checks actually run in a pull request. Original source is licensed under MIT.
