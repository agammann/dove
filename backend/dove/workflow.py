import io
import json
import re
import secrets
import time
import zipfile
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from email.utils import parseaddr
from fastapi import HTTPException
from sqlalchemy import select
from reportlab.pdfgen import canvas
from . import storage, providers
from .config import settings
from .db import Organization, Record, add, get, records, update


def require(condition, message, status=409):
    if not condition:
        raise HTTPException(status, message)


def event(db, org, work, message, actor="system"):
    return add(db, org, "activity", {"message": message, "actor": actor}, work)


def enqueue(db, org, work, kind, key, payload=None, due=None):
    existing = db.scalar(
        select(Record).where(
            Record.org_id == org, Record.kind == "job", Record.dedupe == key
        )
    )
    if existing:
        return existing
    return add(
        db,
        org,
        "job",
        {
            "type": kind,
            "payload": payload or {},
            "status": "pending",
            "attempts": 0,
            "due": due or time.time(),
            "error": None,
        },
        work,
        key,
    )


def mutable(db, work):
    attempts = records(db, work.org_id, "delivery", work.id)
    require(
        not any(a.data["status"] in ("sending", "uncertain") for a in attempts),
        "A send is in progress or uncertain. Reconcile it before changing this work item",
    )


def invalidate(db, work, reason):
    mutable(db, work)
    update(work, revision=work.data.get("revision", 0) + 1)
    for p in records(db, work.org_id, "package", work.id):
        if p.data.get("approval") and not p.data.get("delivered"):
            update(p, approval=None, invalidation=reason)


def state(db, work):
    if work.data.get("archived"):
        update(work, status="archived", blocker="Archived")
        return
    deliveries = records(db, work.org_id, "delivery", work.id)
    packages = records(db, work.org_id, "package", work.id)
    current = packages[-1] if packages else None
    current_attempts = [
        d
        for d in deliveries
        if d.data.get("package_id") == (current.id if current else None)
    ]
    if (
        current_attempts
        and current
        and current.data["revision"] == work.data["revision"]
    ):
        ds = current_attempts[-1].data["status"]
        if ds in ("sending", "pending"):
            update(work, status="sending", blocker="Delivery queued or in progress")
            return
        if ds in ("provider_accepted", "delivered"):
            update(
                work,
                status="sent",
                blocker="Provider accepted the message"
                if ds == "provider_accepted"
                else "Delivery confirmed by provider",
            )
            return
        if ds in ("failed", "uncertain", "bounced"):
            update(
                work,
                status="failed",
                blocker="Delivery uncertain: reconcile before retrying"
                if ds == "uncertain"
                else "Delivery failed: review the attempt",
            )
            return
    if any(
        d.data["status"] == "open"
        for d in records(db, work.org_id, "decision", work.id)
    ):
        update(work, status="needs_decision", blocker="Resolve the open decision")
        return
    reqs = records(db, work.org_id, "requirement", work.id)
    if not work.data.get("confirmed"):
        update(
            work,
            status="reviewing"
            if records(db, work.org_id, "document", work.id)
            else "draft",
            blocker="Review and confirm requirements",
        )
        return
    if any(r.data["status"] in ("received", "needs_review") for r in reqs):
        update(work, status="reviewing", blocker="Review received evidence")
        return
    if any(r.data["status"] == "missing" for r in reqs):
        update(
            work,
            status="waiting_for_information",
            blocker="Missing information needs an authorized request",
        )
        return
    if (
        current
        and current.data.get("approval")
        and current.data["revision"] == work.data["revision"]
    ):
        update(
            work,
            status="approved",
            blocker="Authorize delivery of the approved package",
        )
        return
    update(
        work,
        status="ready_for_approval",
        blocker="Build and approve the billing package",
    )


def current_documents(db, work):
    return [
        d
        for d in records(db, work.org_id, "document", work.id)
        if d.data.get("current", True)
    ]


def upload(db, org, work_id, filename, content, actor, role="internal", pages=None):
    work = get(db, org, work_id, "work")
    require(
        len(current_documents(db, work)) < 30
        or any(d.data["filename"] == filename for d in current_documents(db, work)),
        "Maximum 30 current documents per work item",
    )
    require(
        len(records(db, org, "document", work_id))
        < settings.max_document_versions_per_work,
        "Retained document version allowance reached for this work item",
    )
    if pages is None:
        pages = storage.extract(filename, content, org)
    invalidate(db, work, "A document version changed")
    previous = [
        d for d in current_documents(db, work) if d.data["filename"] == filename
    ]
    version = max([d.data["version"] for d in previous] + [0]) + 1
    for d in previous:
        update(d, current=False)
    key, digest = storage.store(org, content)
    doc = add(
        db,
        org,
        "document",
        {
            "filename": filename,
            "version": version,
            "pages": pages,
            "sha256": digest,
            "storage_key": key,
            "role": role,
            "approved_support": False,
            "current": True,
            "size": len(content),
        },
        work_id,
    )
    update(work, confirmed=False)
    for r in records(db, org, "requirement", work_id):
        update(
            r,
            status="needs_review",
            review_reason="Documents changed; re-check evidence",
        )
    for req in records(db, org, "request", work_id):
        update(req, stopped=True)
    enqueue(
        db,
        org,
        work_id,
        "analyze",
        "analyze-" + doc.id,
        {"revision": work.data["revision"]},
    )
    event(
        db,
        org,
        work_id,
        f"Document added: {filename}, version {version}. Approvals require reevaluation.",
        actor,
    )
    state(db, work)
    return doc


def perform_analysis(db, work):
    docs = current_documents(db, work)
    require(bool(docs), "Upload a document first")
    inputs = [
        {"id": d.id, "version": d.data["version"], "pages": d.data["pages"]}
        for d in docs
    ]
    require(
        sum(len(p) for d in inputs for p in d["pages"])
        < settings.max_model_input_chars,
        "Analysis exceeds input budget; split the work item",
    )
    analysis, usage = providers.analyze(inputs)
    byid = {d.id: d for d in docs}
    grouped = {}
    for proposal in analysis.requirements:
        src = proposal.source
        doc = byid.get(src.document_id)
        require(
            doc
            and doc.data["version"] == src.version
            and src.page <= len(doc.data["pages"]),
            "Model source reference was invalid; review manually",
        )
        page = doc.data["pages"][src.page - 1]
        require(
            src.excerpt in page and (not src.value or src.value in src.excerpt),
            "Model evidence was not grounded in the document; review manually",
        )
        evidence = add(
            db,
            work.org_id,
            "evidence",
            {
                **src.model_dump(),
                "line": page[: page.index(src.excerpt)].count("\n") + 1,
                "review_status": "unreviewed",
                "origin": "document",
            },
            work.id,
        )
        grouped.setdefault(proposal.category, []).append((proposal, evidence))
    existing = {
        r.data["category"]: r for r in records(db, work.org_id, "requirement", work.id)
    }
    for category, proposals in grouped.items():
        received = [p for p, e in proposals if p.status == "received"]
        status = "received" if received else "missing"
        values = {
            p.source.value.replace(",", "") for p, e in proposals if p.source.value
        }
        if category == "amount" and len(values) > 1:
            status = "needs_review"
            decision(
                db,
                work,
                "Conflicting amounts appear in the source documents.",
                "Confirm the agreed amount against the original agreement. Correct the invoice or obtain a documented change approval.",
                [e.id for p, e in proposals],
                "amount-conflict-" + str(work.data["revision"]),
            )
        data = {
            "category": category,
            "title": proposals[0][0].title,
            "status": status,
            "evidence_ids": [e.id for p, e in proposals],
            "reason": "Proposed by local fixture rules"
            if usage["simulated"]
            else "Proposed from document evidence",
            "reviewed_by": None,
        }
        if category in existing:
            existing[category].data = data
        else:
            add(db, work.org_id, "requirement", data, work.id)
    if not grouped:
        decision(
            db,
            work,
            "No billing requirements were identified.",
            "Add requirements manually or upload a readable agreement with billing instructions.",
            [],
            "empty-" + str(work.data["revision"]),
        )
    add(db, work.org_id, "usage", usage, work.id)
    event(
        db,
        work.org_id,
        work.id,
        "Analysis complete. Review source excerpts and confirm the checklist."
        + (" Local rules; simulated model." if usage["simulated"] else ""),
    )
    state(db, work)


def decision(db, work, question, consequence, evidence_ids, key):
    existing = db.scalar(
        select(Record).where(
            Record.org_id == work.org_id,
            Record.kind == "decision",
            Record.dedupe == key,
        )
    )
    if existing:
        return existing
    return add(
        db,
        work.org_id,
        "decision",
        {
            "question": question,
            "why": "This affects whether the work is ready for invoicing.",
            "consequence": consequence,
            "evidence_ids": evidence_ids,
            "status": "open",
        },
        work.id,
        key,
    )


def review_requirement(db, work, requirement, data, actor):
    invalidate(db, work, "Requirement review changed")
    for eid in data.evidence_ids:
        e = get(db, work.org_id, eid, "evidence")
        require(e.work_id == work.id, "Evidence belongs to a different work item")
        if e.data.get("document_id"):
            doc = get(db, work.org_id, e.data["document_id"], "document")
            require(
                doc.data["current"], "Use evidence from the current document version"
            )
    if data.status == "satisfied":
        require(
            bool(data.evidence_ids), "Satisfied requirements need inspectable evidence"
        )
    values = data.model_dump()
    values["reviewed_by"] = actor
    values["reviewed_at"] = time.time()
    if data.status == "waived":
        values["reason"] = (
            "Internal authorized waiver; not customer acceptance. " + data.reason
        )
    if requirement:
        requirement.data = values
    else:
        requirement = add(db, work.org_id, "requirement", values, work.id)
    for eid in data.evidence_ids:
        update(
            get(db, work.org_id, eid, "evidence"),
            review_status="reviewed",
            reviewed_by=actor,
        )
    if data.status != "missing":
        for req in records(db, work.org_id, "request", work.id):
            if requirement.id in req.data["requirement_ids"]:
                update(req, stopped=True)
    event(
        db,
        work.org_id,
        work.id,
        f"{data.title}: {data.status}. {values['reason']}",
        actor,
    )
    state(db, work)
    return requirement


def authorized_contact(db, work, cid):
    c = get(db, work.org_id, cid, "contact")
    require(
        c.data["authorized"] and c.data["customer_id"] == work.data["customer_id"],
        "Recipient must be an authorized contact for this customer",
        403,
    )
    return c


def business_due(now, timezone, days):
    local = datetime.fromtimestamp(now, ZoneInfo(timezone))
    remaining = days
    while remaining:
        local += timedelta(days=1)
        if local.weekday() < 5:
            remaining -= 1
    return local.replace(hour=9, minute=0, second=0, microsecond=0).timestamp()


def create_request(db, work, data, actor):
    mutable(db, work)
    require(work.data.get("confirmed"), "Confirm the requirement checklist first")
    require(data.follow_up_permission, "Explicit follow-up permission is required")
    org = db.get(Organization, work.org_id)
    require(
        not org.data.get("automation_paused") and not work.data.get("paused"),
        "Automation is paused",
    )
    contact = authorized_contact(db, work, data.contact_id)
    titles = []
    for rid in data.requirement_ids:
        r = get(db, work.org_id, rid, "requirement")
        require(
            r.work_id == work.id and r.data["status"] == "missing",
            "Only recognized missing requirements can be requested",
        )
        require(
            not any(
                rid in req.data["requirement_ids"] and not req.data.get("stopped")
                for req in records(db, work.org_id, "request", work.id)
            ),
            "An active request already covers this requirement",
        )
        titles.append(r.data["title"])
    req = add(
        db,
        work.org_id,
        "request",
        {
            "requirement_ids": data.requirement_ids,
            "contact_id": contact.id,
            "recipient": contact.data["email"],
            "route_token": secrets.token_hex(20),
            "follow_up_permission": True,
            "stopped": False,
            "reminders_sent": 0,
            "status": "queued",
            "body": data.body
            or "Please provide the following for "
            + work.data["title"]
            + ":\n"
            + "\n".join("- " + t for t in titles)
            + "\nReply to this message with the missing information or readable PDF/TXT documents. Your reply will be reviewed before approval.",
            "authorized_by": actor,
        },
        work.id,
    )
    queue_outreach(db, work, req, 0)
    event(
        db,
        work.org_id,
        work.id,
        "Information request authorized for " + contact.data["email"],
        actor,
    )
    state(db, work)
    return req


def queue_outreach(db, work, req, reminder):
    reserve_message(db, work)
    key = "request-" + req.id + "-" + str(reminder)
    attempt = add(
        db,
        work.org_id,
        "delivery",
        {
            "type": "request",
            "request_id": req.id,
            "reminder": reminder,
            "status": "pending",
            "recipient": [req.data["recipient"]],
            "subject": ("Reminder: " if reminder else "")
            + "Information needed · "
            + work.data["title"],
            "body": req.data["body"],
            "provider_id": None,
            "simulated": settings.email_adapter == "local",
            "key": key,
        },
        work.id,
        key,
    )
    enqueue(db, work.org_id, work.id, "send", key, {"attempt_id": attempt.id})
    return attempt


def process_incoming(db, work, incoming, use_model=True):
    data = incoming.data
    if data.get("processed"):
        return
    req = get(db, work.org_id, data["request_id"], "request")
    require(req.work_id == work.id, "Reply route mismatch")
    update(incoming, processed=True)
    if data.get("out_of_office"):
        update(incoming, classification="out_of_office")
        event(
            db,
            work.org_id,
            work.id,
            "Out-of-office reply recorded; no requirement was satisfied.",
        )
        return
    contact = get(db, work.org_id, req.data["contact_id"], "contact")
    relevant_ids = set()
    explanation = "Model allowance unavailable; inspect the complete reply manually."
    if use_model:
        try:
            requested = [
                get(db, work.org_id, rid, "requirement")
                for rid in req.data["requirement_ids"]
            ]
            interpretation, usage = providers.interpret_reply(
                data.get("text", "")[:20000],
                [
                    {
                        "id": r.id,
                        "title": r.data["title"],
                        "category": r.data["category"],
                    }
                    for r in requested
                ],
            )
            for association in interpretation.associations:
                require(
                    association.requirement_id in req.data["requirement_ids"]
                    and association.excerpt in data.get("text", ""),
                    "Reply proposal was not grounded",
                )
                relevant_ids.add(association.requirement_id)
            explanation = interpretation.explanation
            update(
                incoming,
                classification=interpretation.classification,
                interpretation=explanation,
            )
            add(
                db,
                work.org_id,
                "usage",
                {**usage, "purpose": "reply interpretation"},
                work.id,
            )
        except Exception:
            explanation = "Automatic interpretation could not finish. Review the full reply manually."
    update(incoming, interpretation=explanation)
    valid_sender = (
        parseaddr(data.get("sender", ""))[1].lower() == contact.data["email"].lower()
        and contact.data["authorized"]
    )
    ev = add(
        db,
        work.org_id,
        "evidence",
        {
            "origin": "incoming",
            "incoming_id": incoming.id,
            "excerpt": data.get("text", "")[:1500] or "[Attachment-only reply]",
            "value": "",
            "review_status": "unreviewed",
            "sender": data.get("sender"),
            "sender_authentication": data.get("sender_authentication", "unknown"),
            "forwarded": data.get("forwarded", False),
        },
        work.id,
    )
    for rid in req.data["requirement_ids"]:
        r = get(db, work.org_id, rid, "requirement")
        require(r.work_id == work.id, "Reply requirement scope mismatch")
        if rid in relevant_ids and r.data["status"] in (
            "missing",
            "received",
            "needs_review",
        ):
            update(
                r,
                status="received"
                if valid_sender and not data.get("forwarded")
                else "needs_review",
                evidence_ids=r.data.get("evidence_ids", []) + [ev.id],
            )
    # Reply evidence cannot authorize acceptance, even with a verified provider event.
    decision(
        db,
        work,
        "Review the reply before treating it as evidence or customer acceptance.",
        "Verify the sender, relevance, authority and any attachments. Internal approval does not establish customer acceptance. "
        + explanation
        + (
            " This reply may be forwarded or from an unauthorized sender."
            if not valid_sender or data.get("forwarded")
            else ""
        ),
        [ev.id],
        "reply-" + incoming.id,
    )
    update(req, status="replied", stopped=True)
    if not any(
        a.data["status"] in ("sending", "uncertain")
        for a in records(db, work.org_id, "delivery", work.id)
    ):
        invalidate(db, work, "New reply evidence requires review")
    else:
        # Preserve the historical sent package. The new evidence remains an open decision.
        event(
            db,
            work.org_id,
            work.id,
            "Late reply received during delivery; existing delivery snapshot remains immutable.",
        )
    event(
        db,
        work.org_id,
        work.id,
        "Reply persisted and associated with its request. Workflow resumed for human review.",
    )
    state(db, work)


def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def supported_amount(evidence, amount, currency="USD"):
    prefix = re.escape(currency) + (r"|\$" if currency == "USD" else "")
    candidates = re.findall(
        r"(?:" + prefix + r")\s*(\d[\d,]*(?:\.\d{1,2})?)(?!\d)",
        evidence.data["excerpt"],
        re.I,
    )
    return any(money(v.replace(",", "")) == amount for v in candidates)


def pdf_invoice(manifest):
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=(595, 842))
    c.setTitle("Invoice " + manifest["invoice_number"])
    y = 790
    lines = [
        manifest["business"]["business_name"],
        manifest["business"]["billing_details"],
        "",
        "INVOICE " + manifest["invoice_number"],
        "Customer: " + manifest["customer"]["name"],
        "Issue date: " + manifest["issue_date"],
        "Due date: " + manifest["due_date"],
        "Currency: " + manifest["currency"],
        "",
    ]
    for item in manifest["line_items"]:
        lines.append(
            f"{item['description']} | {item['quantity']} x {item['unit_price']} = {item['total']}"
        )
    lines += [
        "",
        "Tax (entered by operator): " + manifest["tax"],
        "Discount: " + manifest["discount"],
        "TOTAL: " + manifest["currency"] + " " + manifest["total"],
    ]
    import textwrap

    for line in lines:
        for part in textwrap.wrap(line, width=88) or [""]:
            if y < 60:
                c.showPage()
                y = 790
            c.setFont("Helvetica", 11)
            c.drawString(42, y, part)
            y -= 19
    c.save()
    return out.getvalue()


def build_package(db, work, data, actor):
    mutable(db, work)
    require(
        len(records(db, work.org_id, "package", work.id))
        < settings.max_package_versions_per_work,
        "Package version allowance reached",
    )
    state(db, work)
    require(
        work.data["status"] in ("ready_for_approval", "approved", "sent", "failed"),
        "Resolve all requirements and decisions before building a package",
    )
    require(
        data.details_confirmed,
        "Confirm customer/business details, dates, amounts, taxes and discounts",
    )
    org = db.get(Organization, work.org_id)
    require(
        org.data.get("business_name") and org.data.get("billing_details"),
        "Complete business billing details in Settings",
    )
    require(
        date.fromisoformat(data.due_date) >= date.fromisoformat(data.issue_date),
        "Due date must not precede issue date",
    )
    customer = get(db, work.org_id, work.data["customer_id"], "customer")
    contacts = [authorized_contact(db, work, cid) for cid in set(data.contact_ids)]
    docs = []
    for did in set(data.document_ids):
        doc = get(db, work.org_id, did, "document")
        require(
            doc.work_id == work.id
            and doc.data["current"]
            and doc.data["approved_support"],
            "Supporting documents must be current and approved for customer delivery",
        )
        require(
            doc.data["role"] == "support",
            "Internal evidence cannot become a customer attachment",
        )
        docs.append(doc)
    line_items = []
    total = money(data.confirmed_total)
    if data.mode == "generated":
        require(bool(data.line_items), "A generated invoice needs confirmed line items")
        subtotal = Decimal("0")
        used_sources = set()
        for line in data.line_items:
            e = get(db, work.org_id, line.evidence_id, "evidence")
            source_key = (
                e.data.get("document_id", e.data.get("incoming_id")),
                e.data.get("page"),
                e.data["excerpt"],
            )
            require(
                source_key not in used_sources,
                "A charge source cannot be counted twice; provide distinct approved evidence for each line",
            )
            used_sources.add(source_key)
            amount = money(Decimal(line.quantity) * Decimal(line.unit_price))
            require(
                Decimal(line.quantity) > 0 and amount > 0,
                "Line quantities and amounts must be positive",
            )
            require(
                e.work_id == work.id
                and e.data["review_status"] == "reviewed"
                and supported_amount(e, amount, work.data["currency"]),
                "Every charge must match reviewed source evidence in this currency; unsupported charges cannot be invoiced",
            )
            if e.data.get("document_id"):
                require(
                    get(db, work.org_id, e.data["document_id"], "document").data[
                        "current"
                    ],
                    "Charge evidence must reference a current document",
                )
            require(
                any(
                    r.data["category"] == "amount"
                    and r.data["status"] == "satisfied"
                    and e.id in r.data.get("evidence_ids", [])
                    for r in records(db, work.org_id, "requirement", work.id)
                ),
                "Charge evidence must satisfy a reviewed amount requirement",
            )
            subtotal += amount
            line_items.append({**line.model_dump(), "total": str(amount)})
        calculated = money(subtotal + money(data.tax) - money(data.discount))
        require(
            calculated >= 0 and calculated == total,
            "Confirmed total must equal line totals plus entered tax minus discount",
        )
    else:
        require(data.invoice_document_id, "Select the existing invoice PDF")
        doc = get(db, work.org_id, data.invoice_document_id, "document")
        require(
            doc.work_id == work.id
            and doc.data["current"]
            and doc.data["filename"].lower().endswith(".pdf"),
            "The existing invoice must be a current PDF from this work item",
        )
        docs = [d for d in docs if d.id != doc.id]
        invoice_doc = doc
    invalidate(db, work, "New package version built")
    number = org.data.get("invoice_counter", 0) + 1
    org.data = {**org.data, "invoice_counter": number}
    all_docs = docs + ([invoice_doc] if data.mode == "existing" else [])
    version = len(records(db, work.org_id, "package", work.id)) + 1
    manifest = {
        "version": version,
        "invoice_number": f"DV-{number:06d}",
        "invoice_mode": data.mode,
        "work_id": work.id,
        "title": work.data["title"],
        "currency": work.data["currency"],
        "business": {k: org.data[k] for k in ("business_name", "billing_details")},
        "customer": customer.data,
        "recipients": sorted(c.data["email"] for c in contacts),
        "contact_ids": sorted(c.id for c in contacts),
        "issue_date": data.issue_date,
        "due_date": data.due_date,
        "line_items": line_items,
        "tax": str(money(data.tax)),
        "discount": str(money(data.discount)),
        "total": str(total),
        "summary": data.summary,
        "documents": [
            {
                "id": d.id,
                "version": d.data["version"],
                "sha256": d.data["sha256"],
                "filename": d.data["filename"],
            }
            for d in all_docs
        ],
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True, indent=2).encode()
    invoice = (
        pdf_invoice(manifest)
        if data.mode == "generated"
        else storage.read(work.org_id, invoice_doc.data["storage_key"])
    )
    package_bytes = io.BytesIO()
    with zipfile.ZipFile(package_bytes, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("invoice.pdf", invoice)
        z.writestr("completion-summary.txt", data.summary)
        z.writestr("manifest.json", manifest_bytes)
        for d in docs:
            z.writestr(
                "support/" + d.id[:8] + "-" + d.data["filename"],
                storage.read(work.org_id, d.data["storage_key"]),
            )
    require(
        package_bytes.tell() <= settings.max_package_bytes,
        "Package exceeds 20 MB; use fewer supporting documents",
    )
    key, digest = storage.store(work.org_id, package_bytes.getvalue())
    pkg = add(
        db,
        work.org_id,
        "package",
        {
            "version": version,
            "manifest": manifest,
            "digest": digest,
            "size": package_bytes.tell(),
            "storage_key": key,
            "revision": work.data["revision"],
            "approval": None,
            "delivered": False,
            "created_by": actor,
        },
        work.id,
    )
    event(
        db,
        work.org_id,
        work.id,
        f"Billing package version {version} assembled. Review exact attachments and recipients.",
        actor,
    )
    state(db, work)
    return pkg


def approve_package(db, work, package, data, actor):
    require(
        data.authorize and data.digest == package.data["digest"],
        "Explicit approval of this exact package digest is required",
    )
    state(db, work)
    require(
        work.data["status"] in ("ready_for_approval", "approved"),
        "Work item has unresolved requirements or decisions",
    )
    require(
        package.data["revision"] == work.data["revision"],
        "Package changed; rebuild and review it",
    )
    for cid in package.data["manifest"]["contact_ids"]:
        authorized_contact(db, work, cid)
    update(
        package,
        approval={
            "actor": actor,
            "at": time.time(),
            "digest": data.digest,
            "revision": work.data["revision"],
        },
    )
    event(
        db,
        work.org_id,
        work.id,
        "Exact package, amounts, recipients and document versions approved internally.",
        actor,
    )
    state(db, work)


def deliver_package(db, work, package, data, actor):
    require(
        data.authorize and data.digest == package.data["digest"],
        "Authorize delivery of the exact approved package",
    )
    require(
        package.data.get("approval")
        and package.data["revision"] == work.data["revision"],
        "Package approval is missing or invalidated",
    )
    require(
        not any(
            d.data.get("package_id") == package.id
            for d in records(db, work.org_id, "delivery", work.id)
        ),
        "A delivery attempt already exists; inspect its status",
    )
    for cid in package.data["manifest"]["contact_ids"]:
        authorized_contact(db, work, cid)
    reserve_message(db, work)
    key = "package-" + package.id
    attempt = add(
        db,
        work.org_id,
        "delivery",
        {
            "type": "package",
            "package_id": package.id,
            "status": "pending",
            "recipient": package.data["manifest"]["recipients"],
            "subject": "Billing package · " + work.data["title"],
            "body": package.data["manifest"]["summary"]
            + "\n\nThe approved invoice and supporting documents are attached. Sending does not indicate acceptance or payment.",
            "provider_id": None,
            "simulated": settings.email_adapter == "local",
            "key": key,
            "authorized_by": actor,
        },
        work.id,
        key,
    )
    enqueue(db, work.org_id, work.id, "send", key, {"attempt_id": attempt.id})
    event(
        db,
        work.org_id,
        work.id,
        "Delivery explicitly authorized for approved package version "
        + str(package.data["version"]),
        actor,
    )
    state(db, work)
    return attempt


def reserve_message(db, work):
    # One durable allowance includes initial attempts and definite rejection
    # retries, across outreach and package delivery. Caller holds org lock.
    attempts = records(db, work.org_id, "delivery", work.id)
    used = sum(1 + a.data.get("retries", 0) for a in attempts)
    require(used < settings.max_messages_per_item, "Message allowance reached")
