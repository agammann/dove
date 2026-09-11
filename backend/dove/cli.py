import argparse
import json
import secrets
import time
from sqlalchemy import select, delete
from .config import settings
from .db import (
    Organization,
    User,
    Invitation,
    Record,
    Session,
    SessionLocal,
    transaction,
    add,
    records,
)
from .auth import token_hash, passwords
from . import workflow as w

SAMPLES = [
    (
        "Northline Studio",
        "studio@dove.example",
        "Alder & Co.",
        "Brand identity handoff",
        "Purchase order required before invoicing.\nCustomer acceptance: final brand identity accepted by Morgan at Alder & Co.\nApproved deliverables: final brand guide delivered.\nAgreed amount USD 2400.00.\nBilling recipient: morgan@alder.example",
        "morgan@alder.example",
    ),
    (
        "Fieldwork Consulting",
        "consulting@dove.example",
        "Juniper Group",
        "Operations review",
        "Agreement amount USD 4800.00.\nInvoice amount USD 5200.00.\nCustomer acceptance: operations review accepted.\nBilling recipient: robin@juniper.example",
        "robin@juniper.example",
    ),
    (
        "Common Ground IT",
        "it@dove.example",
        "Cedar Research",
        "Workspace migration",
        "Customer acceptance required before invoicing.\nCompletion checklist required before invoicing.\nAgreed amount USD 1800.00.\nBilling recipient: sam@cedar.example",
        "sam@cedar.example",
    ),
]


def seed(reset=False):
    if (
        settings.environment != "local"
        or settings.model_adapter != "fixture"
        or settings.email_adapter != "local"
    ):
        raise SystemExit("Sample seed/reset is restricted to local fixture mode")
    with transaction() as db:
        for name, email, customer_name, title, agreement, contact_email in SAMPLES:
            existing = db.scalar(select(User).where(User.email == email))
            if existing:
                if not reset:
                    continue
                org = db.get(Organization, existing.org_id)
                if not org.data.get("sample"):
                    raise SystemExit("Refusing to reset a non-sample organization")
                from .main import remove_work

                for work in records(db, org.id, "work"):
                    # Sample reset only: local sends have no external effects.
                    for a in records(db, org.id, "delivery", work.id):
                        a.data = {**a.data, "status": "cancelled"}
                    remove_work(db, org.id, work)
                for model in (Record, Session, Invitation, User):
                    stmt = delete(model).where(model.org_id == org.id)
                    if model is Record:
                        stmt = stmt.where(Record.kind != "file_gc")
                    db.execute(stmt)
                db.delete(org)
                db.flush()
            org = Organization(
                name=name,
                data={
                    "sample": True,
                    "business_name": name,
                    "billing_details": "Fictional sample business · 100 Example Lane",
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
                    email=email,
                    password_hash=passwords.hash("Dove-local-sample-2026!"),
                )
            )
            customer = add(db, org.id, "customer", {"name": customer_name})
            contact = add(
                db,
                org.id,
                "contact",
                {
                    "customer_id": customer.id,
                    "customer": customer_name,
                    "name": contact_email.split("@")[0].title(),
                    "email": contact_email,
                    "authorized": True,
                    "acceptance_authority": True,
                },
            )
            work = add(
                db,
                org.id,
                "work",
                {
                    "title": title,
                    "description": "Fictional completed service work for the sample workspace.",
                    "contact_id": contact.id,
                    "customer_id": customer.id,
                    "customer": customer_name,
                    "currency": "USD",
                    "status": "draft",
                    "blocker": "Review requirements",
                    "revision": 0,
                    "confirmed": False,
                    "paused": False,
                },
            )
            w.upload(db, org.id, work.id, "Agreement.txt", agreement.encode(), email)
            w.event(
                db,
                org.id,
                work.id,
                "Fictional sample workspace. All model and email actions are simulated.",
            )
    from .worker import tick

    tick(30)
    print(
        "Sample accounts ready: studio@dove.example, consulting@dove.example, it@dove.example"
    )
    print("Local sample password: Dove-local-sample-2026!")


def invite(org_name, email):
    from pydantic import TypeAdapter, EmailStr

    email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    token = secrets.token_urlsafe(32)
    with transaction() as db:
        org = db.scalar(select(Organization).where(Organization.name == org_name))
        if not org:
            org = Organization(
                name=org_name,
                data={
                    "sample": False,
                    "timezone": "UTC",
                    "reminder_limit": 2,
                    "reminder_business_days": 2,
                    "automation_paused": True,
                },
            )
            db.add(org)
            db.flush()
        db.add(
            Invitation(
                token_hash=token_hash(token),
                org_id=org.id,
                email=email,
                expires=time.time() + 72 * 3600,
            )
        )
    print(
        "Invitation created for "
        + email
        + "; expires in 72 hours. Share privately with the intended recipient:"
    )
    print(settings.public_url + "/invite#" + token)


def main():
    p = argparse.ArgumentParser(description="Dove operator CLI")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    sub.add_parser("reset-samples")
    i = sub.add_parser("invite")
    i.add_argument("--organization", required=True)
    i.add_argument("--email", required=True)
    sub.add_parser("access-requests")
    args = p.parse_args()
    if args.command in ("seed", "reset-samples"):
        seed(args.command == "reset-samples")
    elif args.command == "invite":
        invite(args.organization, args.email)
    elif args.command == "access-requests":
        with SessionLocal() as db:
            print(
                json.dumps(
                    [r.data for r in records(db, "public", "access_request")], indent=2
                )
            )


if __name__ == "__main__":
    main()
