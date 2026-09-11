import os
import tempfile
from pathlib import Path

os.environ["ENVIRONMENT"] = "local"
os.environ["MODEL_ADAPTER"] = "fixture"
os.environ["EMAIL_ADAPTER"] = "local"
os.environ["STORAGE_DIR"] = tempfile.mkdtemp(prefix="dove-test-objects-")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite:///" + str(Path(tempfile.mkdtemp(prefix="dove-test-db-")) / "test.db"),
)
import pytest
from fastapi.testclient import TestClient
from dove.db import Base, engine, transaction, Organization, User
from dove.auth import passwords
from dove.main import app


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def clients():
    password = "test-only-password-12345"
    result = []
    for i in range(2):
        with transaction() as db:
            org = Organization(
                name=f"Test org {i}",
                data={
                    "business_name": f"Test business {i}",
                    "billing_details": "Fictional address",
                    "timezone": "America/Los_Angeles",
                    "reminder_limit": 2,
                    "reminder_business_days": 2,
                    "automation_paused": False,
                },
            )
            db.add(org)
            db.flush()
            db.add(
                User(
                    org_id=org.id,
                    email=f"test{i}@example.com",
                    password_hash=passwords.hash(password),
                )
            )
        c = TestClient(app)
        c.headers["X-Dove-Action"] = "1"
        assert (
            c.post(
                "/api/auth/login",
                json={"email": f"test{i}@example.com", "password": password},
            ).status_code
            == 200
        )
        result.append(c)
    return result
