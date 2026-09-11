import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor
from svix.webhooks import Webhook
from datetime import datetime, timezone
from sqlalchemy import select
from dove.db import (
    transaction,
    SessionLocal,
    Record,
    Organization,
    get,
    records,
    update,
    add,
)
from dove.config import settings
from dove import worker, workflow as w, providers
from test_workflow import create, detail, review, package, ok, AGREEMENT


def test_expired_send_intent_is_quarantined(clients, monkeypatch):
    c = clients[0]
    work, contact, doc = create(c)
    wid = work["id"]
    review(c, wid, missing=True)
    po = next(r for r in detail(c, wid)["requirement"] if r["status"] == "missing")
    ok(
        c.post(
            "/api/work/" + wid + "/requests",
            json={
                "requirement_ids": [po["id"]],
                "contact_id": contact["id"],
                "follow_up_permission": True,
            },
        )
    )
    with transaction() as db:
        attempt = next(
            a for a in db.scalars(select(Record).where(Record.kind == "delivery"))
        )
        update(attempt, status="sending", started=time.time() - 300)
    calls = []
    monkeypatch.setattr(providers, "send_email", lambda *a, **k: calls.append(a))
    worker.tick()
    assert calls == []
    assert detail(c, wid)["delivery"][0]["status"] == "uncertain"


def test_multiple_workers_cannot_duplicate_send(clients, monkeypatch):
    c = clients[0]
    work, contact, doc = create(c)
    wid = work["id"]
    review(c, wid, missing=True)
    po = next(r for r in detail(c, wid)["requirement"] if r["status"] == "missing")
    ok(
        c.post(
            "/api/work/" + wid + "/requests",
            json={
                "requirement_ids": [po["id"]],
                "contact_id": contact["id"],
                "follow_up_permission": True,
            },
        )
    )
    calls = []

    def send(*a, **k):
        calls.append(1)
        time.sleep(0.15)
        return {"id": "local-provider-id", "status": "provider_accepted"}

    monkeypatch.setattr(providers, "send_email", send)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker.tick(), range(2)))
    assert len(calls) == 1


def test_pause_and_reminder_limits(clients):
    c = clients[0]
    work, contact, doc = create(c)
    wid = work["id"]
    review(c, wid, missing=True)
    po = next(r for r in detail(c, wid)["requirement"] if r["status"] == "missing")
    req = ok(
        c.post(
            "/api/work/" + wid + "/requests",
            json={
                "requirement_ids": [po["id"]],
                "contact_id": contact["id"],
                "follow_up_permission": True,
            },
        )
    )
    ok(c.post("/api/work/" + wid + "/pause"))
    worker.tick()
    assert detail(c, wid)["delivery"][0]["status"] == "pending"
    ok(c.post("/api/work/" + wid + "/pause"))
    with transaction() as db:
        for j in db.scalars(select(Record).where(Record.kind == "job")):
            update(j, due=time.time() - 1)
    worker.tick()
    for _ in range(4):
        with transaction() as db:
            update(db.get(Record, req["id"]), next_reminder=time.time() - 1)
        worker.tick()
    d = detail(c, wid)
    assert len(d["delivery"]) == 3 and d["request"][0]["reminders_sent"] == 2


def test_signed_webhook_persisted_and_deduplicated(clients):
    c = clients[0]
    work, contact, doc = create(c)
    wid = work["id"]
    review(c, wid, missing=True)
    po = next(r for r in detail(c, wid)["requirement"] if r["status"] == "missing")
    req = ok(
        c.post(
            "/api/work/" + wid + "/requests",
            json={
                "requirement_ids": [po["id"]],
                "contact_id": contact["id"],
                "follow_up_permission": True,
            },
        )
    )
    with SessionLocal() as db:
        route = db.get(Record, req["id"]).data["route_token"]
    secret = "whsec_" + base64.b64encode(b"test-secret-value-not-production").decode()
    original = settings.resend_webhook_secret
    settings.resend_webhook_secret = secret
    payload = json.dumps(
        {
            "type": "email.received",
            "data": {
                "email_id": "test-provider-123",
                "from": "morgan@example.com",
                "to": [route + "@" + settings.reply_domain],
            },
        }
    )
    now = datetime.now(timezone.utc)
    event_id = "event-signed-test"
    signature = Webhook(secret).sign(event_id, now, payload)
    headers = {
        "svix-id": event_id,
        "svix-timestamp": str(int(now.timestamp())),
        "svix-signature": signature,
        "content-type": "application/json",
    }
    try:
        ok(c.post("/api/webhooks/resend", content=payload, headers=headers))
        result = ok(c.post("/api/webhooks/resend", content=payload, headers=headers))
        assert result["duplicate"]
        d = detail(c, wid)
        assert len(d["incoming"]) == 1 and not d["incoming"][0]["processed"]
        assert any(
            j["type"] == "hydrate_incoming" and j["status"] == "pending"
            for j in d["job"]
        )
    finally:
        settings.resend_webhook_secret = original


def test_out_of_office_does_not_resolve_missing(clients):
    c = clients[0]
    work, contact, doc = create(c)
    wid = work["id"]
    review(c, wid, missing=True)
    po = next(r for r in detail(c, wid)["requirement"] if r["status"] == "missing")
    req = ok(
        c.post(
            "/api/work/" + wid + "/requests",
            json={
                "requirement_ids": [po["id"]],
                "contact_id": contact["id"],
                "follow_up_permission": True,
            },
        )
    )
    ok(
        c.post(
            "/api/local/inbox",
            json={
                "request_id": req["id"],
                "event_id": "out-of-office",
                "sender": "morgan@example.com",
                "text": "I am away.",
                "out_of_office": True,
            },
        )
    )
    worker.tick()
    assert (
        next(r for r in detail(c, wid)["requirement"] if r["id"] == po["id"])["status"]
        == "missing"
    )


def test_scanned_pdf_actionable_and_existing_invoice_immutable(clients):
    import io
    from reportlab.pdfgen import canvas

    c = clients[0]
    work, contact, doc = create(
        c,
        AGREEMENT.replace(
            "Purchase order required before invoicing.",
            "Purchase order PO-1042 provided.",
        ),
    )
    wid = work["id"]
    blank = io.BytesIO()
    cv = canvas.Canvas(blank)
    cv.showPage()
    cv.save()
    response = c.post(
        "/api/work/" + wid + "/documents",
        files={"file": ("scan.pdf", blank.getvalue(), "application/pdf")},
    )
    assert response.status_code == 422 and "scanned or unreadable" in response.text
    pdf = io.BytesIO()
    cv = canvas.Canvas(pdf)
    cv.drawString(50, 750, "Existing invoice: agreed amount USD 2400.00")
    cv.save()
    inv = ok(
        c.post(
            "/api/work/" + wid + "/documents",
            files={"file": ("existing.pdf", pdf.getvalue(), "application/pdf")},
            data={"role": "invoice"},
        )
    )
    worker.tick()
    review(c, wid)
    p = ok(
        c.post(
            "/api/work/" + wid + "/packages",
            json={
                "mode": "existing",
                "contact_ids": [contact["id"]],
                "document_ids": [],
                "invoice_document_id": inv["id"],
                "line_items": [],
                "confirmed_total": "2400.00",
                "tax": "0",
                "discount": "0",
                "issue_date": "2026-09-08",
                "due_date": "2026-10-08",
                "summary": "Approved completed work.",
                "details_confirmed": True,
            },
        )
    )
    url = ok(c.get("/api/files/" + p["id"] + "/link"))["url"]
    assert c.get(url + "?entry=invoice.pdf").content == pdf.getvalue()


def test_failed_model_calls_consume_budget(clients, monkeypatch):
    c = clients[0]

    def fail(*a):
        raise RuntimeError("Model not available")

    monkeypatch.setattr(providers, "analyze", fail)
    work, contact, doc = create(c)
    d = detail(c, work["id"])
    assert d["work"]["model_calls"] == 1 and d["job"][0]["attempts"] == 1


def test_approved_package_recipient_change_blocks_delivery(clients):
    c = clients[0]
    work, contact, doc = create(
        c,
        AGREEMENT.replace(
            "Purchase order required before invoicing.",
            "Purchase order PO-1042 provided.",
        ),
    )
    wid = work["id"]
    review(c, wid)
    p = ok(package(c, wid, contact["id"]))
    ok(
        c.post(
            "/api/packages/" + p["id"] + "/approve",
            json={"digest": p["digest"], "authorize": True},
        )
    )
    ok(
        c.put(
            "/api/contacts/" + contact["id"],
            json={
                "customer": "Example customer",
                "name": "Morgan",
                "email": "new@example.com",
                "authorized": True,
                "acceptance_authority": True,
            },
        )
    )
    assert (
        c.post(
            "/api/packages/" + p["id"] + "/deliver",
            json={"digest": p["digest"], "authorize": True},
        ).status_code
        == 409
    )
