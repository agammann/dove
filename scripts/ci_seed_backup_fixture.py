"""Seed one fictional object in the disposable Compose CI fixture only."""

import os

if os.environ.get("DOVE_SYNTHETIC_BACKUP_FIXTURE") != "isolated-ci-only":
    raise SystemExit("This script is only for an isolated synthetic fixture.")

from dove.config import settings
from dove.db import Organization, Record, transaction
from dove.storage import store

if settings.environment != "local" or settings.model_adapter != "fixture" or settings.email_adapter != "local":
    raise SystemExit("Synthetic fixture adapters are required.")

org = "synthetic-backup-fixture"
with transaction() as db:
    db.add(Organization(id=org, name="Synthetic backup fixture", data={}))
with transaction(org) as db:
    key, digest = store(org, b"fictional document for backup verification")
    db.add(Record(id="synthetic-backup-document", org_id=org, kind="document", data={"storage_key": key, "sha256": digest}))
