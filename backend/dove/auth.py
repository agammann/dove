import hashlib
import secrets
import time
from fastapi import Request, HTTPException
from pwdlib import PasswordHash
from sqlalchemy import select
from .db import SessionLocal, Session, User, Record, add, transaction

passwords = PasswordHash.recommended()
dummy_hash = passwords.hash(secrets.token_urlsafe(32))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def authenticate(request: Request):
    token = request.cookies.get("dove_session", "")
    with SessionLocal() as db:
        session = db.get(Session, token_hash(token))
        if not session or session.expires < time.time():
            raise HTTPException(401, "Sign in with an invitation-based account")
        user = db.get(User, session.user_id)
        if not user or user.org_id != session.org_id:
            raise HTTPException(401, "Session is no longer valid")
        return user


def rate_limit(scope, identity, allowance, seconds):
    # Persistent counters, keyed by hashed IP/account. No plaintext addresses in counters.
    key = scope + "-" + token_hash(identity) + "-" + str(int(time.time()) // seconds)
    with transaction() as db:
        row = db.scalar(
            select(Record)
            .where(
                Record.org_id == "public",
                Record.kind == "rate_limit",
                Record.dedupe == key,
            )
            .with_for_update()
        )
        if not row:
            row = add(db, "public", "rate_limit", {"count": 0}, dedupe=key)
        if row.data["count"] >= allowance:
            raise HTTPException(429, "Too many requests. Please try again later")
        row.data = {"count": row.data["count"] + 1}
