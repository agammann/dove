# Dove progress

Updated September 19, 2026, Pacific time.

The [public website](https://dove-paperwork.alx21.chatgpt.site) is live and accepts early access requests. The [GitHub repository](https://github.com/agammann/dove) contains the separately runnable document workspace. No open source license has been selected for the original code.

1. Implemented: organization isolation, invitations, durable jobs, bounded PDF/TXT uploads and evidence review.
2. Implemented: editable request drafts, explicit contact authorization, persisted replies, human decisions and bounded reminders.
3. Implemented: immutable invoice packages, exact previews, separate approval and delivery, export and deletion.
4. Verified locally: 30 tests each on SQLite and PostgreSQL; full HTTP workflow with a separate worker; authenticated package download; browser preview; backup and isolated restore.
5. Fixed during verification: absent database restart policy and known Vite/Playwright development dependency advisories. Updated setup, development, operations and deployment directions.
6. Verified publicly: website workflow navigation and access request persistence. The website does not create customer workspace accounts or send automatic emails.
7. Pending: secure OpenAI key setup and live inference, Resend domain and authorized email tests, full workspace hosting, operational release gates and a real business pilot.

See [validation](docs/VALIDATION.md) for dated evidence and [release checklist](docs/RELEASE-CHECKLIST.md) for remaining work. Local adapters are simulated. Passing tests does not establish provider accuracy, production readiness or customer demand.
