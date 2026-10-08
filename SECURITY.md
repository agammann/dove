# Security reporting

For a private security concern, use [GitHub private vulnerability reporting](https://github.com/agammann/dove/security/advisories/new). Include the affected version, source location and a minimal fictional reproduction. Do not publish customer records, credentials or workspace backups in an issue.

Browser v1 stores local records and backup ZIPs without encryption. API keys stay in tab memory and are supplied only to the optional analysis request. Review the [data and storage guide](docs/HOSTED-WORKSPACE.md) and [supported v1 scope](docs/STABILITY.md). The separately runnable Python sample needs its own provider and deployment configuration before customer use.

For routine defects or missing documentation, open a normal issue using fictional data. Dependency audit output is available in CI; run the locked checks and apply available patches when changing dependencies.
