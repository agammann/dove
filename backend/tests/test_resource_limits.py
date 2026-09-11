import io
import subprocess
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from reportlab.pdfgen import canvas
from dove.config import settings
from dove import pdf_process, worker
from test_workflow import create, detail, review, package, ok, AGREEMENT


def ready(c):
    work, contact, doc = create(
        c,
        AGREEMENT.replace(
            "Purchase order required before invoicing.",
            "Purchase order PO-1042 provided.",
        ),
    )
    review(c, work["id"])
    return work, contact, doc


def test_retained_versions_and_bytes_count(clients, monkeypatch):
    c = clients[0]
    work, _, _ = create(c)
    monkeypatch.setattr(settings, "max_document_versions_per_work", 2)
    url = "/api/work/" + work["id"] + "/documents"
    ok(c.post(url, files={"file": ("agreement.txt", AGREEMENT.encode())}))
    assert (
        c.post(url, files={"file": ("agreement.txt", AGREEMENT.encode())}).status_code
        == 409
    )
    assert len(detail(c, work["id"])["document"]) == 2
    monkeypatch.setattr(settings, "max_document_versions_per_work", 100)
    monkeypatch.setattr(settings, "max_org_storage_bytes", len(AGREEMENT.encode()) * 2)
    assert (
        c.post(url, files={"file": ("agreement.txt", AGREEMENT.encode())}).status_code
        == 409
    )


def test_package_allowance_and_no_duplicate_charge(clients, monkeypatch):
    c = clients[0]
    work, contact, _ = ready(c)
    import json

    valid = package(c, work["id"], contact["id"])
    body = json.loads(valid.request.content)
    body["line_items"] *= 2
    body["confirmed_total"] = "4800.00"
    duplicate = c.post("/api/work/" + work["id"] + "/packages", json=body)
    assert duplicate.status_code == 409
    assert "source" in duplicate.text.lower()
    monkeypatch.setattr(settings, "max_package_versions_per_work", 2)
    first = ok(package(c, work["id"], contact["id"]))
    assert package(c, work["id"], contact["id"]).status_code == 409
    monkeypatch.setattr(settings, "max_package_versions_per_work", 20)
    monkeypatch.setattr(settings, "max_org_storage_bytes", 1)
    assert package(c, work["id"], contact["id"]).status_code == 409
    assert len(detail(c, work["id"])["package"]) == 2


def test_draft_is_scoped_and_does_not_authorize_send(clients, monkeypatch):
    c, other = clients
    work, _, _ = create(c)
    url = "/api/work/" + work["id"] + "/request-draft"
    before = detail(c, work["id"])["work"]["model_calls"]
    assert other.post(url).status_code == 404
    draft = ok(c.post(url))
    assert draft["simulated"] and "purchase order" in draft["body"].lower()
    d = detail(c, work["id"])
    assert d["request"] == [] and d["delivery"] == []
    assert d["work"]["model_calls"] == before + 1
    monkeypatch.setattr(settings, "max_model_calls_per_item", before + 1)
    assert c.post(url).status_code == 409


def test_package_and_retry_share_budget(clients, monkeypatch):
    from dove import providers

    c = clients[0]
    work, contact, _ = ready(c)
    monkeypatch.setattr(settings, "max_messages_per_item", 1)
    p = ok(package(c, work["id"], contact["id"]))
    body = {"digest": p["digest"], "authorize": True}
    ok(c.post("/api/packages/" + p["id"] + "/approve", json=body))
    a = ok(c.post("/api/packages/" + p["id"] + "/deliver", json=body))

    def reject(*a, **k):
        raise providers.RejectedSend("Test rejection")

    monkeypatch.setattr(providers, "send_email", reject)
    worker.tick()
    assert c.post("/api/deliveries/" + a["id"] + "/retry").status_code == 409
    p2 = ok(package(c, work["id"], contact["id"]))
    body2 = {"digest": p2["digest"], "authorize": True}
    ok(c.post("/api/packages/" + p2["id"] + "/approve", json=body2))
    assert (
        c.post("/api/packages/" + p2["id"] + "/deliver", json=body2).status_code == 409
    )


def test_pdf_timeout_and_admission_release(monkeypatch):
    def timeout(*a, **k):
        assert "OPENAI_API_KEY" not in k["env"]
        assert k["timeout"] == 15
        raise subprocess.TimeoutExpired(a[0], 15)

    monkeypatch.setattr(pdf_process.subprocess, "run", timeout)
    for _ in range(2):
        with pytest.raises(Exception) as err:
            pdf_process.process_pdf("test-org", b"%PDF-test")
        assert err.value.status_code == 422
    assert not pdf_process._active


def test_pdf_processing_does_not_block_other_requests(clients, monkeypatch):
    c, other = clients
    work, _, _ = create(c)
    entered, release = threading.Event(), threading.Event()
    original = pdf_process.subprocess.run

    def slow(*a, **k):
        entered.set()
        assert release.wait(5)
        return original(*a, **k)

    monkeypatch.setattr(pdf_process.subprocess, "run", slow)
    doc = io.BytesIO()
    cv = canvas.Canvas(doc)
    cv.drawString(40, 700, "Agreed amount USD 2400.00")
    cv.save()
    with ThreadPoolExecutor(max_workers=2) as pool:
        upload = pool.submit(
            c.post,
            "/api/work/" + work["id"] + "/documents",
            files={"file": ("readable.pdf", doc.getvalue())},
        )
        assert entered.wait(5)
        try:
            assert other.get("/api/health").status_code == 200
            with pytest.raises(Exception) as err:
                pdf_process.process_pdf(
                    ok(c.get("/api/me"))["organization"]["id"], doc.getvalue()
                )
            assert err.value.status_code == 429
        finally:
            release.set()
        ok(upload.result())


def test_exact_invoice_raster_preview(clients):
    c = clients[0]
    work, contact, _ = ready(c)
    p = ok(package(c, work["id"], contact["id"]))
    response = c.get("/api/packages/" + p["id"] + "/preview-page")
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"\x89PNG")
    assert response.headers["x-pdf-pages"] == "1"
    assert (
        clients[1].get("/api/packages/" + p["id"] + "/preview-page").status_code == 404
    )
