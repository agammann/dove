"""Durable DB worker. Sending is a committed intent before any external call.

An expired send lease becomes uncertain, never an automatic retry. Other jobs
retry at most three times. PostgreSQL org-row locks serialize mutations.
"""

import io
import time
import zipfile
from sqlalchemy import select
from .config import settings
from .db import (
    SessionLocal,
    Record,
    Organization,
    transaction,
    records,
    get,
    update,
)
from . import workflow as w, providers, storage


def tick(limit=20):
    purge_files()
    now = time.time()
    with SessionLocal() as db:
        org_ids = list(db.scalars(select(Organization.id)))
    processed = 0
    for org_id in org_ids:
        with transaction(org_id) as db:
            org = db.get(Organization, org_id)
            # Expired send intent is deliberately quarantined, even if the job
            # died before its external call. Exactly-once cannot be assumed.
            for attempt in records(db, org_id, "delivery"):
                if (
                    attempt.data["status"] == "sending"
                    and attempt.data.get("started", 0) < now - 120
                ):
                    update(
                        attempt,
                        status="uncertain",
                        error="Worker stopped during a send. Reconcile provider acceptance before resending.",
                    )
                    work = get(db, org_id, attempt.work_id, "work")
                    w.state(db, work)
            for req in records(db, org_id, "request"):
                work = get(db, org_id, req.work_id, "work")
                if (
                    req.data.get("stopped")
                    or req.data["status"] != "sent"
                    or org.data.get("automation_paused")
                    or work.data.get("paused")
                    or not work.data.get("confirmed")
                ):
                    continue
                if req.data.get("reminders_sent", 0) >= org.data.get(
                    "reminder_limit", 2
                ):
                    continue
                if req.data.get("next_reminder", now + 1) <= now:
                    n = req.data.get("reminders_sent", 0) + 1
                    try:
                        w.queue_outreach(db, work, req, n)
                        update(req, reminders_sent=n, status="queued")
                    except Exception as exc:
                        if getattr(exc, "detail", "") != "Message allowance reached":
                            raise
                        update(req, stopped=True)
                        w.event(
                            db,
                            org_id,
                            work.id,
                            "Reminder stopped: message allowance reached",
                        )
            jobs = [
                j
                for j in records(db, org_id, "job")
                if (j.data["status"] == "pending" and j.data["due"] <= now)
                or (
                    j.data["status"] == "running" and j.data.get("lease_until", 0) < now
                )
            ]
            job_ids = [j.id for j in jobs[: limit - processed]]
        for jid in job_ids:
            if processed >= limit:
                return processed
            process_job(org_id, jid)
            processed += 1
    return processed


def purge_files():
    # Tombstones commit with record deletion. Files are then removed after the
    # transaction, with durable retry if the filesystem temporarily fails.
    with transaction() as db:
        for r in list(
            db.scalars(select(Record).where(Record.kind == "file_gc").with_for_update())
        ):
            path = (settings.storage_dir / r.data["storage_key"]).resolve()
            if not path.is_relative_to(settings.storage_dir.resolve() / r.org_id):
                continue
            try:
                path.unlink(missing_ok=True)
                db.delete(r)
            except OSError:
                pass


def process_job(org_id, jid):
    with transaction(org_id) as db:
        job = get(db, org_id, jid, "job")
        if job.data["status"] not in ("pending", "running"):
            return
        if (
            job.data["status"] == "running"
            and job.data.get("lease_until", 0) > time.time()
        ):
            return
        work = get(db, org_id, job.work_id, "work")
        if work.data.get("archived"):
            update(job, status="cancelled")
            return
        if job.data["type"] == "send" and (
            work.data.get("paused")
            or db.get(Organization, org_id).data.get("automation_paused")
        ):
            update(job, due=time.time() + 30)
            return
        update(
            job,
            status="running",
            attempts=job.data["attempts"] + 1,
            lease_until=time.time() + 120,
        )
    try:
        use_model = True
        if job.data["type"] in ("analyze", "incoming", "hydrate_incoming"):
            # Reserve the allowance durably even if inference fails or the process
            # crashes. A rollback must never refund a potentially billable call.
            with transaction(org_id) as db:
                work = get(db, org_id, job.work_id, "work")
                calls = work.data.get("model_calls", 0)
                if calls >= settings.max_model_calls_per_item:
                    w.require(
                        job.data["type"] != "analyze",
                        "Model call allowance reached; continue with manual review",
                    )
                    use_model = False
                else:
                    update(work, model_calls=calls + 1)
        if job.data["type"] == "send":
            send_job(org_id, jid)
        elif job.data["type"] == "hydrate_incoming":
            with SessionLocal() as db:
                msg = get(db, org_id, job.data["payload"]["incoming_id"], "incoming")
                provider_id = msg.data["provider_id"]
            remote = providers.retrieve_email(provider_id, received=True)
            with transaction(org_id) as db:
                msg = get(db, org_id, job.data["payload"]["incoming_id"], "incoming")
                headers = {
                    k.lower(): v for k, v in (remote.get("headers") or {}).items()
                }
                # Header claims are preserved as evidence; never automatically trusted.
                update(
                    msg,
                    sender=remote.get("from", ""),
                    text=(remote.get("text") or "")[:20000],
                    sender_authentication=str(
                        headers.get("authentication-results", "unknown")
                    )[:1500],
                    forwarded=bool(remote.get("received_for"))
                    or "forwarded" in str(remote.get("subject", "")).lower(),
                    out_of_office=headers.get("auto-submitted", "no") != "no",
                    provider_message_id=remote.get("message_id"),
                    attachments=remote.get("attachments", [])[:10],
                )
                work = get(db, org_id, job.work_id, "work")
                if remote.get("attachments"):
                    w.decision(
                        db,
                        work,
                        "Incoming attachments require inspection.",
                        "Retrieve the bounded PDF/TXT attachments from the message view; unsupported attachments require a readable replacement.",
                        [],
                        "attachments-" + msg.id,
                    )
                w.process_incoming(db, work, msg, use_model=use_model)
        else:
            with transaction(org_id) as db:
                job = get(db, org_id, jid, "job")
                work = get(db, org_id, job.work_id, "work")
                if job.data["type"] == "analyze":
                    if job.data["payload"].get("revision") == work.data["revision"]:
                        w.perform_analysis(db, work)
                elif job.data["type"] == "incoming":
                    w.process_incoming(
                        db,
                        work,
                        get(db, org_id, job.data["payload"]["incoming_id"], "incoming"),
                        use_model=use_model,
                    )
                else:
                    raise ValueError("Unknown job type")
        with transaction(org_id) as db:
            update(get(db, org_id, jid, "job"), status="complete", error=None)
    except Exception as exc:
        with transaction(org_id) as db:
            job = get(db, org_id, jid, "job")
            error = getattr(exc, "detail", None) or (
                str(exc)
                if isinstance(exc, (ValueError, RuntimeError))
                else "Processing failed. Check provider configuration or input and retry."
            )
            update(
                job,
                status="failed" if job.data["attempts"] >= 3 else "pending",
                due=time.time() + 60 * job.data["attempts"],
                error=error,
            )
            w.event(db, org_id, job.work_id, "Background job needs attention: " + error)


def send_job(org_id, jid):
    with transaction(org_id) as db:
        job = get(db, org_id, jid, "job")
        attempt = get(db, org_id, job.data["payload"]["attempt_id"], "delivery")
        w.require(
            attempt.work_id == job.work_id, "Job/attempt organization or work mismatch"
        )
        if attempt.data["status"] != "pending":
            return
        work = get(db, org_id, job.work_id, "work")
        attachments = None
        if attempt.data["type"] == "request":
            req = get(db, org_id, attempt.data["request_id"], "request")
            contact = w.authorized_contact(db, work, req.data["contact_id"])
            if req.data.get("stopped") or not work.data.get("confirmed"):
                update(attempt, status="cancelled")
                return
            w.require(
                req.data["follow_up_permission"]
                and req.data["recipient"] == contact.data["email"],
                "Outreach permission or recipient changed",
            )
            w.require(
                all(
                    get(db, org_id, rid, "requirement").data["status"] == "missing"
                    for rid in req.data["requirement_ids"]
                ),
                "Requested items are no longer missing",
            )
            reply_to = req.data["route_token"] + "@" + settings.reply_domain
        else:
            pkg = get(db, org_id, attempt.data["package_id"], "package")
            w.require(
                pkg.work_id == work.id
                and pkg.data.get("approval")
                and pkg.data["revision"] == work.data["revision"],
                "Package approval was invalidated",
            )
            for cid in pkg.data["manifest"]["contact_ids"]:
                w.authorized_contact(db, work, cid)
            content = storage.read(org_id, pkg.data["storage_key"])
            w.require(
                hashlib_sha(content) == pkg.data["digest"],
                "Stored package failed integrity verification",
            )
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                attachments = [
                    (name.split("/")[-1], z.read(name)) for name in z.namelist()
                ]
            reply_to = settings.email_from
        update(attempt, status="sending", started=time.time())
        attempt_data = dict(attempt.data)
    # External action after a committed send intent. No transaction retries here.
    try:
        result = providers.send_email(
            attempt_data["key"],
            attempt_data["recipient"],
            attempt_data["subject"],
            attempt_data["body"],
            reply_to,
            attachments,
        )
        status = result["status"]
        error = None
    except providers.RejectedSend as exc:
        result = {}
        status = "failed"
        error = str(exc)
    except Exception:
        result = {}
        status = "uncertain"
        error = "Provider acceptance is unknown. Reconcile this attempt; Dove will not automatically resend."
    with transaction(org_id) as db:
        attempt = get(db, org_id, attempt.id, "delivery")
        update(
            attempt,
            status=status,
            provider_id=result.get("id"),
            error=error,
            finished=time.time(),
        )
        work = get(db, org_id, attempt.work_id, "work")
        if attempt.data["type"] == "request":
            req = get(db, org_id, attempt.data["request_id"], "request")
            org = db.get(Organization, org_id)
            update(
                req,
                status="sent" if status == "provider_accepted" else status,
                next_reminder=w.business_due(
                    time.time(),
                    org.data.get("timezone", "UTC"),
                    org.data.get("reminder_business_days", 2),
                ),
            )
        elif status == "provider_accepted":
            update(
                get(db, org_id, attempt.data["package_id"], "package"), delivered=True
            )
        w.event(
            db,
            org_id,
            work.id,
            "Email attempt: "
            + status
            + (
                ". Local outbox; simulated sending."
                if attempt.data["simulated"]
                else "."
            ),
        )
        w.state(db, work)


def hashlib_sha(data):
    import hashlib

    return hashlib.sha256(data).hexdigest()


def main():
    settings.validate_deployment()
    print("Dove worker started; adapter=" + settings.email_adapter, flush=True)
    while True:
        try:
            tick()
        except Exception:
            # Ordinary logs deliberately exclude user documents and provider payloads.
            print(
                "Worker tick failed; inspect health and scoped job failures.",
                flush=True,
            )
        time.sleep(2)


if __name__ == "__main__":
    main()
