import io
import json
import secrets
import time
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import select, delete, text
from svix.webhooks import Webhook, WebhookVerificationError
from .config import settings
from .db import (
    SessionLocal,
    Organization,
    User,
    Invitation,
    Session,
    Record,
    transaction,
    add,
    get,
    records,
    public,
    update,
)
from .auth import authenticate, token_hash, passwords, dummy_hash, rate_limit
from . import schemas as s, workflow as w, storage, providers


@asynccontextmanager
async def lifespan(app):
    settings.validate_deployment()
    yield


app = FastAPI(
    title="Dove",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.environment == "local" else None,
)
signer = URLSafeTimedSerializer(settings.secret_key, salt="dove-download")


@app.middleware("http")
async def boundaries(request, call_next):
    if (
        request.method not in ("GET", "HEAD", "OPTIONS")
        and request.url.path != "/api/webhooks/resend"
    ):
        origin = request.headers.get("origin")
        if origin and origin != settings.public_url:
            return JSONResponse({"detail": "Cross-origin write blocked"}, 403)
        if request.headers.get("x-dove-action") != "1":
            return JSONResponse({"detail": "Missing same-origin action header"}, 403)
    try:
        if (
            int(request.headers.get("content-length", "0"))
            > settings.max_upload_bytes + 1024 * 128
        ):
            return JSONResponse({"detail": "Request too large"}, 413)
    except ValueError:
        return JSONResponse({"detail": "Invalid content length"}, 400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/download/"):
        # The app may preview its own authenticated PDF/text response, while
        # other origins remain unable to frame it. No active HTML is served.
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'"
        )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Exception)
async def recoverable_error(request, exc):
    return JSONResponse(
        {
            "detail": "The operation could not complete. Your saved work is preserved. Retry or inspect activity and job status."
        },
        500,
    )


@app.get("/api/health")
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/config")
def config():
    return {
        "local": settings.environment == "local",
        "model_adapter": settings.model_adapter,
        "email_adapter": settings.email_adapter,
    }


@app.post("/api/access-requests", status_code=201)
def access_request(data: s.AccessRequest, request: Request):
    rate_limit("access", request.client.host, 5, 3600)
    w.require(data.consent and not data.website, "Consent is required", 422)
    with transaction() as db:
        add(
            db,
            "public",
            "access_request",
            {**data.model_dump(exclude={"website"}), "status": "new"},
        )
    return {
        "message": "Your access request is saved. Invitation access is reviewed manually."
    }


@app.post("/api/auth/login")
def login(data: s.Login, request: Request, response: Response):
    rate_limit("login-ip", request.client.host, 20, 900)
    rate_limit("login-account", str(data.email).lower(), 10, 900)
    with transaction() as db:
        user = db.scalar(select(User).where(User.email == str(data.email).lower()))
        valid = passwords.verify(
            data.password, user.password_hash if user else dummy_hash
        )
        if not user or not valid:
            raise HTTPException(401, "Email or password is incorrect")
        token = secrets.token_urlsafe(40)
        db.add(
            Session(
                token_hash=token_hash(token),
                org_id=user.org_id,
                user_id=user.id,
                expires=time.time() + settings.session_hours * 3600,
            )
        )
        response.set_cookie(
            "dove_session",
            token,
            httponly=True,
            secure=settings.environment != "local",
            samesite="strict",
            max_age=settings.session_hours * 3600,
            path="/",
        )
    return {"ok": True}


@app.post("/api/auth/accept-invitation")
def accept_invitation(data: s.AcceptInvite, request: Request):
    rate_limit("invite", request.client.host, 10, 3600)
    with transaction() as db:
        invite = db.scalar(
            select(Invitation)
            .where(Invitation.token_hash == token_hash(data.token))
            .with_for_update()
        )
        w.require(
            invite
            and not invite.used
            and invite.expires > time.time()
            and invite.email == str(data.email).lower(),
            "Invitation is invalid or expired",
            403,
        )
        w.require(
            not db.scalar(select(User).where(User.email == str(data.email).lower())),
            "This account already exists",
            409,
        )
        db.add(
            User(
                org_id=invite.org_id,
                email=str(data.email).lower(),
                password_hash=passwords.hash(data.password),
            )
        )
        invite.used = 1
    return {"ok": True}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        db.execute(
            delete(Session).where(
                Session.token_hash
                == token_hash(request.cookies.get("dove_session", "")),
                Session.org_id == user.org_id,
            )
        )
    response.delete_cookie("dove_session")
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(authenticate)):
    with SessionLocal() as db:
        org = db.get(Organization, user.org_id)
        return {
            "email": user.email,
            "organization": {"id": org.id, "name": org.name, **org.data},
            "local": settings.environment == "local",
            "model_adapter": settings.model_adapter,
            "email_adapter": settings.email_adapter,
        }


@app.get("/api/contacts")
def contacts(user=Depends(authenticate)):
    with SessionLocal() as db:
        return [public(c) for c in records(db, user.org_id, "contact")]


@app.post("/api/contacts", status_code=201)
def create_contact(data: s.ContactInput, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        customers = records(db, user.org_id, "customer")
        customer = next((c for c in customers if c.data["name"] == data.customer), None)
        if not customer:
            customer = add(db, user.org_id, "customer", {"name": data.customer})
        c = add(
            db,
            user.org_id,
            "contact",
            {**data.model_dump(mode="json"), "customer_id": customer.id},
        )
        return public(c)


@app.put("/api/contacts/{id}")
def edit_contact(id: str, data: s.ContactInput, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        c = get(db, user.org_id, id, "contact")
        for work in records(db, user.org_id, "work"):
            if work.data["customer_id"] == c.data["customer_id"]:
                w.invalidate(db, work, "Contact or recipient authorization changed")
                w.decision(
                    db,
                    work,
                    "Customer contact details or authority changed.",
                    "Review the authorized recipients and rebuild any affected package.",
                    [],
                    "contact-" + id + "-" + str(work.data["revision"]),
                )
                for req in records(db, user.org_id, "request", work.id):
                    if req.data["contact_id"] == id:
                        update(req, stopped=True)
                w.state(db, work)
        c.data = {**data.model_dump(mode="json"), "customer_id": c.data["customer_id"]}
        return public(c)


@app.get("/api/work")
def list_work(user=Depends(authenticate)):
    with SessionLocal() as db:
        return [public(r) for r in records(db, user.org_id, "work")]


@app.post("/api/work", status_code=201)
def create_work(data: s.WorkInput, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        w.require(
            len(records(db, user.org_id, "work")) < 500,
            "Workspace limit reached; export or remove older work",
        )
        contact = get(db, user.org_id, data.contact_id, "contact")
        work = add(
            db,
            user.org_id,
            "work",
            {
                **data.model_dump(),
                "customer_id": contact.data["customer_id"],
                "customer": contact.data["customer"],
                "status": "draft",
                "blocker": "Upload documents to begin",
                "revision": 0,
                "confirmed": False,
                "paused": False,
                "model_calls": 0,
            },
        )
        w.event(db, user.org_id, work.id, "Work item created", user.email)
        return public(work)


@app.get("/api/work/{id}")
def detail(id: str, user=Depends(authenticate)):
    with SessionLocal() as db:
        work = get(db, user.org_id, id, "work")
        result = {"work": public(work)}
        for kind in (
            "document",
            "requirement",
            "evidence",
            "request",
            "incoming",
            "decision",
            "package",
            "delivery",
            "job",
            "activity",
            "usage",
        ):
            result[kind] = [public(r) for r in records(db, user.org_id, kind, id)]
        return result


@app.post("/api/work/{id}/documents", status_code=201)
def upload(
    id: str,
    file: UploadFile = File(...),
    role: str = Form("internal"),
    user=Depends(authenticate),
):
    w.require(role in ("internal", "support", "invoice"), "Invalid document role", 422)
    with SessionLocal() as db:
        get(db, user.org_id, id, "work")
    rate_limit("document", user.org_id, 30, 3600)
    content = file.file.read(settings.max_upload_bytes + 1)
    filename = Path((file.filename or "document").replace("\\", "/")).name
    w.require(
        0 < len(filename) <= 180 and "\n" not in filename and "\r" not in filename,
        "Invalid filename",
        422,
    )
    pages = storage.extract(filename, content, user.org_id)
    with transaction(user.org_id) as db:
        return public(
            w.upload(
                db, user.org_id, id, filename, content, user.email, role, pages=pages
            )
        )


@app.post("/api/documents/{id}/approve-support")
def approve_support(id: str, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        doc = get(db, user.org_id, id, "document")
        work = get(db, user.org_id, doc.work_id, "work")
        w.require(
            doc.data["role"] == "support" and doc.data["current"],
            "Only current documents explicitly uploaded as customer support can be approved",
        )
        w.invalidate(db, work, "Supporting document approval changed")
        update(doc, approved_support=True)
        w.event(
            db,
            user.org_id,
            work.id,
            "Supporting document approved for customer delivery: "
            + doc.data["filename"],
            user.email,
        )
        return public(doc)


@app.put("/api/requirements/{id}")
def edit_requirement(id: str, data: s.RequirementInput, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        r = get(db, user.org_id, id, "requirement")
        work = get(db, user.org_id, r.work_id, "work")
        return public(w.review_requirement(db, work, r, data, user.email))


@app.post("/api/work/{id}/requirements")
def add_requirement(id: str, data: s.RequirementInput, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        return public(
            w.review_requirement(
                db, get(db, user.org_id, id, "work"), None, data, user.email
            )
        )


@app.post("/api/work/{id}/confirm")
def confirm(id: str, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        work = get(db, user.org_id, id, "work")
        w.mutable(db, work)
        w.require(
            bool(records(db, user.org_id, "requirement", id)),
            "Add or analyze requirements first",
        )
        w.require(
            not any(
                j.data["type"] == "analyze"
                and j.data["status"] in ("pending", "running")
                for j in records(db, user.org_id, "job", id)
            ),
            "Wait for document analysis to finish",
        )
        update(work, confirmed=True, confirmed_by=user.email)
        w.event(
            db,
            user.org_id,
            id,
            "Requirement checklist confirmed. Outreach still requires explicit authorization.",
            user.email,
        )
        w.state(db, work)
        return public(work)


@app.post("/api/work/{id}/pause")
def pause(id: str, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        work = get(db, user.org_id, id, "work")
        update(work, paused=not work.data.get("paused"))
        w.event(
            db,
            user.org_id,
            id,
            "Automation paused" if work.data["paused"] else "Automation resumed",
            user.email,
        )
        return public(work)


@app.post("/api/work/{id}/requests")
def request_info(id: str, data: s.RequestInput, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        return public(
            w.create_request(db, get(db, user.org_id, id, "work"), data, user.email)
        )


@app.post("/api/work/{id}/request-draft")
def request_draft(id: str, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        work = get(db, user.org_id, id, "work")
        missing = [
            {"id": r.id, "title": r.data["title"]}
            for r in records(db, user.org_id, "requirement", id)
            if r.data["status"] == "missing"
        ]
        w.require(missing, "There are no missing requirements to request")
        calls = work.data.get("model_calls", 0)
        w.require(
            calls < settings.max_model_calls_per_item,
            "Model allowance reached; write the request manually",
        )
        update(work, model_calls=calls + 1)
        title = work.data["title"]
    draft, usage = providers.draft_request(title, missing)
    with transaction(user.org_id) as db:
        get(db, user.org_id, id, "work")
        add(db, user.org_id, "usage", {**usage, "purpose": "request drafting"}, id)
    return {"body": draft.body, "simulated": usage["simulated"]}


@app.post("/api/requests/{id}/stop")
def stop_request(id: str, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        r = get(db, user.org_id, id, "request")
        update(r, stopped=True)
        w.event(
            db,
            user.org_id,
            r.work_id,
            "Follow-up permission revoked; remaining reminders stopped.",
            user.email,
        )
    return {"ok": True}


@app.get("/api/decisions")
def decisions(user=Depends(authenticate)):
    with SessionLocal() as db:
        return [
            {**public(d), "work_id": d.work_id}
            for d in records(db, user.org_id, "decision")
        ]


@app.post("/api/decisions/{id}/resolve")
def resolve_decision(id: str, data: s.DecisionInput, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        d = get(db, user.org_id, id, "decision")
        work = get(db, user.org_id, d.work_id, "work")
        w.require(d.data["status"] == "open", "This decision was already resolved")
        w.invalidate(db, work, "Decision changed")
        update(
            d,
            status="resolved",
            resolution=data.model_dump(),
            resolved_by=user.email,
            resolved_at=time.time(),
        )
        if data.requirement_id:
            r = get(db, user.org_id, data.requirement_id, "requirement")
            w.require(r.work_id == work.id, "Requirement scope mismatch")
            update(
                r,
                status="waived" if data.action == "waive" else "needs_review",
                reason=data.explanation,
                reviewed_by=user.email,
            )
        w.event(
            db,
            user.org_id,
            work.id,
            "Decision resolved ("
            + data.action
            + "): "
            + data.explanation
            + ". Requirements still need explicit review.",
            user.email,
        )
        w.state(db, work)
        return public(d)


@app.post("/api/work/{id}/packages")
def package(id: str, data: s.PackageInput, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        return public(
            w.build_package(db, get(db, user.org_id, id, "work"), data, user.email)
        )


@app.post("/api/packages/{id}/{action}")
def package_action(
    id: str, action: str, data: s.ApprovalInput, user=Depends(authenticate)
):
    with transaction(user.org_id) as db:
        pkg = get(db, user.org_id, id, "package")
        work = get(db, user.org_id, pkg.work_id, "work")
        if action == "approve":
            w.approve_package(db, work, pkg, data, user.email)
        elif action == "deliver":
            return public(w.deliver_package(db, work, pkg, data, user.email))
        else:
            raise HTTPException(404)
        return public(pkg)


@app.get("/api/files/{id}/link")
def file_link(id: str, user=Depends(authenticate)):
    with SessionLocal() as db:
        record = get(db, user.org_id, id)
        w.require(
            record.kind in ("document", "package"), "No file for this record", 404
        )
    return {
        "url": "/api/download/"
        + signer.dumps({"id": id, "org": user.org_id, "user": user.id})
    }


@app.get("/api/packages/{id}/preview-page")
def preview_package_page(id: str, page: int = 0, user=Depends(authenticate)):
    import base64
    from .pdf_process import process_pdf

    rate_limit("preview", user.org_id, 60, 60)
    with SessionLocal() as db:
        pkg = get(db, user.org_id, id, "package")
        content = storage.read(user.org_id, pkg.data["storage_key"])
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            pdf = z.read("invoice.pdf")
    result = process_pdf(user.org_id, pdf, "preview", page)
    return Response(
        base64.b64decode(result["png"]),
        media_type="image/png",
        headers={"X-PDF-Pages": str(result["count"])},
    )


@app.get("/api/download/{token}")
def download(token: str, entry: str | None = None, user=Depends(authenticate)):
    try:
        payload = signer.loads(token, max_age=300)
    except (BadSignature, SignatureExpired):
        raise HTTPException(403, "Download expired; request a fresh link")
    w.require(
        payload["org"] == user.org_id and payload["user"] == user.id,
        "Download is not authorized for this account",
        403,
    )
    with SessionLocal() as db:
        r = get(db, user.org_id, payload["id"])
        content = storage.read(user.org_id, r.data["storage_key"])
        filename = r.data.get(
            "filename", "dove-package-v" + str(r.data.get("version", 1)) + ".zip"
        )
        if entry:
            w.require(r.kind == "package", "Entry preview requires a package", 422)
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                w.require(entry in z.namelist(), "Entry not found", 404)
                content = z.read(entry)
                filename = Path(entry).name
        media = (
            "application/pdf"
            if filename.endswith(".pdf")
            else "text/plain; charset=utf-8"
            if filename.endswith((".txt", ".json"))
            else "application/zip"
        )
        from urllib.parse import quote

        disposition = "inline" if media != "application/zip" else "attachment"
        return Response(
            content,
            media_type=media,
            headers={
                "Content-Disposition": disposition
                + "; filename*=UTF-8''"
                + quote(filename)
            },
        )


@app.put("/api/settings")
def update_settings(data: s.SettingsInput, user=Depends(authenticate)):
    try:
        ZoneInfo(data.timezone)
    except Exception:
        raise HTTPException(
            422, "Use a valid IANA timezone, such as America/Los_Angeles"
        )
    with transaction(user.org_id) as db:
        org = db.get(Organization, user.org_id)
        billing_changed = any(
            org.data.get(k) != getattr(data, k)
            for k in ("business_name", "billing_details")
        )
        if billing_changed:
            for work in records(db, user.org_id, "work"):
                w.invalidate(db, work, "Business billing details changed")
                w.state(db, work)
        org.data = {**org.data, **data.model_dump()}
    return {"ok": True}


@app.post("/api/jobs/{id}/retry")
def retry_job(id: str, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        job = get(db, user.org_id, id, "job")
        w.require(
            job.data["status"] == "failed" and job.data["type"] != "send",
            "Only failed processing jobs can be retried; inspect delivery attempts separately",
        )
        update(job, status="pending", attempts=0, due=time.time())
    return {"ok": True}


@app.post("/api/deliveries/{id}/reconcile")
def reconcile(id: str, user=Depends(authenticate)):
    with SessionLocal() as db:
        attempt = get(db, user.org_id, id, "delivery")
        w.require(
            attempt.data.get("provider_id") and not attempt.data["simulated"],
            "No provider ID is available. Investigate this attempt with the provider; automatic resend remains blocked",
        )
        pid = attempt.data["provider_id"]
    remote = providers.retrieve_email(pid)
    with transaction(user.org_id) as db:
        a = get(db, user.org_id, id, "delivery")
        status = remote.get("last_event")
        mapping = {
            "delivered": "delivered",
            "bounced": "bounced",
            "failed": "failed",
            "sent": "provider_accepted",
        }
        w.require(
            status in mapping, "Provider status is still inconclusive; do not resend"
        )
        update(a, status=mapping[status])
        w.state(db, get(db, user.org_id, a.work_id, "work"))
        return public(a)


@app.post("/api/deliveries/{id}/retry")
def retry_delivery(id: str, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        a = get(db, user.org_id, id, "delivery")
        w.require(
            a.data["status"] == "failed" and not a.data.get("provider_id"),
            "Retry is allowed only after a definite provider rejection; uncertain or accepted sends cannot be retried",
        )
        work = get(db, user.org_id, a.work_id, "work")
        w.require(a.data.get("retries", 0) < 3, "Manual retry limit reached")
        w.reserve_message(db, work)
        update(a, status="pending", retries=a.data.get("retries", 0) + 1)
        w.enqueue(
            db,
            user.org_id,
            work.id,
            "send",
            a.id + "-retry-" + str(a.data["retries"]),
            {"attempt_id": a.id},
        )
    return {"ok": True}


@app.post("/api/local/inbox")
def local_inbox(data: s.LocalReply, user=Depends(authenticate)):
    w.require(
        settings.environment == "local" and settings.email_adapter == "local",
        "Local inbox is disabled",
        404,
    )
    with transaction(user.org_id) as db:
        req = get(db, user.org_id, data.request_id, "request")
        existing = db.scalar(
            select(Record).where(
                Record.org_id == user.org_id,
                Record.kind == "incoming",
                Record.dedupe == data.event_id,
            )
        )
        if existing:
            return public(existing)
        msg = add(
            db,
            user.org_id,
            "incoming",
            {
                **data.model_dump(mode="json"),
                "simulated": True,
                "processed": False,
                "sender_authentication": "local fixture; not verified",
            },
            req.work_id,
            data.event_id,
        )
        w.enqueue(
            db,
            user.org_id,
            req.work_id,
            "incoming",
            "incoming-" + msg.id,
            {"incoming_id": msg.id},
        )
        return public(msg)


@app.post("/api/incoming/{id}/attachments/{attachment_id}")
def incoming_attachment(id: str, attachment_id: str, user=Depends(authenticate)):
    with SessionLocal() as db:
        msg = get(db, user.org_id, id, "incoming")
        w.require(
            not msg.data.get("simulated"),
            "Use a direct local upload for simulated attachments",
        )
        attachment = next(
            (a for a in msg.data.get("attachments", []) if a["id"] == attachment_id),
            None,
        )
        w.require(
            attachment is not None,
            "Attachment does not belong to this incoming message",
            404,
        )
        w.require(
            attachment.get("filename", "").lower().endswith((".txt", ".pdf")),
            "Request a readable PDF or TXT version of this attachment",
            422,
        )
        provider_id = msg.data["provider_id"]
    filename, content = providers.retrieve_attachment(provider_id, attachment_id)
    filename = Path(filename.replace("\\", "/")).name
    rate_limit("document", user.org_id, 30, 3600)
    pages = storage.extract(filename, content, user.org_id)
    with transaction(user.org_id) as db:
        msg = get(db, user.org_id, id, "incoming")
        old = next(
            (
                a.get("document_id")
                for a in msg.data.get("attachments", [])
                if a["id"] == attachment_id
            ),
            None,
        )
        if old:
            return public(get(db, user.org_id, old, "document"))
        doc = w.upload(
            db,
            user.org_id,
            msg.work_id,
            filename,
            content,
            user.email,
            "internal",
            pages=pages,
        )
        update(
            msg,
            attachments=[
                {**a, **({"document_id": doc.id} if a["id"] == attachment_id else {})}
                for a in msg.data["attachments"]
            ],
        )
        return public(doc)


@app.post("/api/webhooks/resend")
async def webhook(request: Request):
    w.require(bool(settings.resend_webhook_secret), "Webhook is not configured", 503)
    body = await request.body()
    w.require(len(body) < 256000, "Webhook too large", 413)
    try:
        Webhook(settings.resend_webhook_secret).verify(body, dict(request.headers))
        payload = json.loads(body)
        if not isinstance(payload, dict) or not isinstance(
            payload.get("data", {}), dict
        ):
            raise ValueError("Invalid webhook envelope")
    except (WebhookVerificationError, ValueError):
        raise HTTPException(400, "Invalid webhook signature")
    event_id = request.headers["svix-id"]
    data = payload.get("data", {})
    with SessionLocal() as db:
        # Routing uses an unguessable dedicated address plus provider event IDs,
        # never a subject match. The organization is derived from the stored route.
        if payload.get("type") == "email.received":
            addresses = data.get("to", [])
            matches = [
                r
                for r in db.scalars(select(Record).where(Record.kind == "request"))
                if r.data["route_token"] + "@" + settings.reply_domain in addresses
            ]
        else:
            matches = [
                r
                for r in db.scalars(select(Record).where(Record.kind == "delivery"))
                if r.data.get("provider_id") == data.get("email_id")
                and data.get("email_id")
            ]
        if len(matches) != 1:
            # Persist unmatched signed events for operations review, without routing
            # their contents to any customer organization.
            org_id = "public"
            target = None
        else:
            target = matches[0]
            org_id = target.org_id
    with transaction(org_id if org_id != "public" else None) as db:
        if db.scalar(
            select(Record).where(
                Record.org_id == org_id,
                Record.kind == "webhook",
                Record.dedupe == event_id,
            )
        ):
            return {"accepted": True, "duplicate": True}
        add(
            db,
            org_id,
            "webhook",
            {
                "type": payload.get("type"),
                "provider_id": data.get("email_id"),
                "matched": target is not None,
            },
            target.work_id if target else None,
            event_id,
        )
        if not target:
            return {"accepted": True}
        if target.kind == "request":
            existing = db.scalar(
                select(Record).where(
                    Record.org_id == org_id,
                    Record.kind == "incoming",
                    Record.dedupe == data["email_id"],
                )
            )
            if not existing:
                msg = add(
                    db,
                    org_id,
                    "incoming",
                    {
                        "request_id": target.id,
                        "provider_id": data["email_id"],
                        "sender": data.get("from", ""),
                        "text": "",
                        "processed": False,
                        "simulated": False,
                    },
                    target.work_id,
                    data["email_id"],
                )
                w.enqueue(
                    db,
                    org_id,
                    target.work_id,
                    "hydrate_incoming",
                    "hydrate-" + msg.id,
                    {"incoming_id": msg.id},
                )
        else:
            a = get(db, org_id, target.id, "delivery")
            status = {
                "email.delivered": "delivered",
                "email.bounced": "bounced",
                "email.failed": "failed",
            }.get(payload.get("type"))
            if status:
                update(a, status=status)
                if a.data.get("request_id") and status in ("bounced", "failed"):
                    update(
                        get(db, org_id, a.data["request_id"], "request"),
                        stopped=True,
                        status=status,
                    )
                w.event(db, org_id, a.work_id, "Provider event: " + status)
                w.state(db, get(db, org_id, a.work_id, "work"))
    return {"accepted": True}


@app.get("/api/settings/export")
def export_workspace(user=Depends(authenticate)):
    import tempfile

    rate_limit("export", user.org_id, 3, 3600)
    out = tempfile.TemporaryFile()
    with SessionLocal() as db:
        rows = list(db.scalars(select(Record).where(Record.org_id == user.org_id)))
        data = {
            "organization": db.get(Organization, user.org_id).data,
            "records": [
                {"kind": r.kind, "work_id": r.work_id, **public(r)} for r in rows
            ],
        }
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("workspace.json", json.dumps(data, indent=2))
            for r in rows:
                if r.kind in ("document", "package"):
                    z.writestr(
                        "files/" + r.id + "/" + r.data.get("filename", "package.zip"),
                        storage.read(user.org_id, r.data["storage_key"]),
                    )
    out.seek(0)

    def chunks():
        try:
            while chunk := out.read(65536):
                yield chunk
        finally:
            out.close()

    return StreamingResponse(
        chunks(),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=dove-workspace-export.zip"
        },
    )


def remove_work(db, org, work):
    w.mutable(db, work)
    for r in list(
        db.scalars(
            select(Record).where(Record.org_id == org, Record.work_id == work.id)
        )
    ):
        if r.data.get("storage_key"):
            path = (settings.storage_dir / r.data["storage_key"]).resolve()
            w.require(
                path.is_relative_to(settings.storage_dir.resolve() / org),
                "Invalid storage path",
            )
            add(db, org, "file_gc", {"storage_key": r.data["storage_key"]})
        db.delete(r)
    db.delete(work)


@app.delete("/api/work/{id}")
def delete_work(id: str, user=Depends(authenticate)):
    with transaction(user.org_id) as db:
        remove_work(db, user.org_id, get(db, user.org_id, id, "work"))
    from .worker import purge_files

    purge_files()
    return {"ok": True, "message": "Work, files, pending jobs and reminders deleted"}


@app.delete("/api/settings/workspace")
def delete_workspace(request: Request, response: Response, user=Depends(authenticate)):
    w.require(
        request.headers.get("x-dove-delete") == "DELETE WORKSPACE",
        "Type DELETE WORKSPACE to confirm deletion",
        422,
    )
    with transaction(user.org_id) as db:
        work_items = records(db, user.org_id, "work")
        for work in work_items:
            w.mutable(db, work)
        for work in work_items:
            remove_work(db, user.org_id, work)
        for model in (Record, Session, Invitation, User):
            stmt = delete(model).where(model.org_id == user.org_id)
            if model is Record:
                stmt = stmt.where(Record.kind != "file_gc")
            db.execute(stmt)
        db.delete(db.get(Organization, user.org_id))
    from .worker import purge_files

    purge_files()
    response.delete_cookie("dove_session")
    return {"ok": True}


frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend.exists():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        candidate = (frontend / path).resolve()
        if candidate.is_relative_to(frontend.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(frontend / "index.html")
