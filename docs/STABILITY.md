# Dove v1

The v1 product is the browser workspace in `sites/`: readable PDF/TXT uploads, source-linked requirements, human review, request drafts and verified reply records, invoice/package downloads, exact version approval, and complete local backup restoration. Device analysis and visitor-funded OpenAI analysis are optional. Manual review and packaging work without either model. The landing page's native WebMCP tool changes an illustration only.

Records belong to one browser profile and full site origin. There is no automatic synchronization, shared workspace, email delivery, acceptance tracking or payment collection. PDF uploads need extractable text; OCR is not included. Source quotes establish attribution, not truth or completeness. Review originals, omissions and agreed payment dates yourself. Use GPT-5.4 for comparisons across documents; a checked mini response omitted the calculated due date. Browser model results can omit requirements even on a short source.

## Install and build

Use Node.js 22.13 or newer and npm. Extract the release ZIP or check out its tag. In `sites/`, run `npm ci`, then `npm run dev`; open `http://127.0.0.1:5173/workspace/`. For a compiled preview, run `npm run build` and `npm start`. Entering a different port creates a separate local workspace.

The repository also includes a separate Python/PostgreSQL example. Its documented Docker setup and fixture tests are supported as an example; browser v1 does not certify its real email, live model provider or customer hosting. Preserve both implementations and their dependency locks.

## Upgrade

1. Export a **complete backup** in Settings and keep it privately outside browser storage. Note the current source release and site address.
2. Verify the release ZIP's checksum against `SHA256SUMS`, extract into a fresh folder, and install from its lockfile. Do not copy `node_modules` or private environment files into a public checkout.
3. Try the fictional browser quickstart in an isolated profile. Deploy the built source to the same origin to retain existing local records. Preserve the managed host's project ID, D1/R2 resources and any previous data.
4. Check the current profile before editing real work. Existing saved requirement and browser backup version 1 formats are retained. Export another backup after successful use.

## Recover and roll back

Restore only complete Dove browser backup ZIPs through Settings. Restore validates structure, record references, quotes, file hashes and package fingerprints before atomically replacing local records/files. Invalid archives leave current work unchanged. Export current work first. Restored packages require renewed approval.

To roll back an application build, redeploy the previous source version to the same origin and check its supported data format. Rolling back code does not undo edits to saved work. Use an earlier complete backup when the records themselves need recovery; inspect restored originals and packages before approving them again. D1/R2 migrations and bindings are retained for legacy records; public browser backups do not export those records.

Local records and backups are not encrypted or authenticated by Dove. Browser data deletion, quota eviction, private browsing and lost profiles can erase work. Keep private backups and test restoration before relying on the app.

## Verification and support

[October 7 verification](verification/v1-2026-10-07.md) distinguishes ordinary browser checks, actual native WebMCP, real WebGPU and live hosted responses. These checks use fictional data. They do not establish general model accuracy, support on all devices or suitability for a particular accounting process.

Report ordinary bugs through [GitHub issues](https://github.com/agammann/dove/issues). Include the release/browser version, fictional reproduction, expected and observed behavior. Do not attach customer records, backup ZIPs or API keys. See [security reporting](../SECURITY.md) for private concerns.
