import secrets
import time
from sqlalchemy import select
from dove.auth import token_hash
from dove.db import transaction, SessionLocal, Invitation, Organization, Record
from test_workflow import create, detail, ok


def test_invitation_single_use_expiry_and_no_public_signup(clients):
    c = clients[0]
    org = ok(c.get("/api/me"))["organization"]["id"]
    token = secrets.token_urlsafe(32)
    with transaction(org) as db:
        db.add(
            Invitation(
                token_hash=token_hash(token),
                org_id=org,
                email="invited@example.com",
                expires=time.time() + 100,
            )
        )
    body = {
        "email": "invited@example.com",
        "password": "long-password-for-test",
        "token": token,
    }
    ok(c.post("/api/auth/accept-invitation", json=body))
    assert c.post("/api/auth/accept-invitation", json=body).status_code == 403
    assert (
        c.post(
            "/api/auth/accept-invitation",
            json={
                **body,
                "token": secrets.token_urlsafe(32),
                "email": "other@example.com",
            },
        ).status_code
        == 403
    )


def test_download_headers_support_same_origin_preview(clients):
    c = clients[0]
    work, contact, doc = create(c)
    url = ok(c.get("/api/files/" + doc["id"] + "/link"))["url"]
    response = c.get(url)
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_source_values_cannot_be_invented(clients, monkeypatch):
    from dove import providers
    from dove.schemas import Analysis

    def bad(docs):
        return Analysis.model_validate(
            {
                "requirements": [
                    {
                        "category": "purchase_order",
                        "title": "Purchase order",
                        "status": "received",
                        "source": {
                            "document_id": docs[0]["id"],
                            "version": 1,
                            "page": 1,
                            "excerpt": "This excerpt does not exist.",
                            "value": "invented PO",
                        },
                    }
                ]
            }
        ), {"adapter": "fixture", "simulated": True}

    monkeypatch.setattr(providers, "analyze", bad)
    c = clients[0]
    work, contact, doc = create(c)
    d = detail(c, work["id"])
    assert not d["requirement"] and "grounded" in d["job"][0]["error"]


def test_workspace_deletion_removes_auth_and_files(clients):
    c = clients[0]
    work, contact, doc = create(c)
    org = ok(c.get("/api/me"))["organization"]["id"]
    ok(
        c.delete(
            "/api/settings/workspace", headers={"X-Dove-Delete": "DELETE WORKSPACE"}
        )
    )
    assert c.get("/api/me").status_code == 401
    with SessionLocal() as db:
        assert db.get(Organization, org) is None
        assert not list(db.scalars(select(Record).where(Record.org_id == org)))
