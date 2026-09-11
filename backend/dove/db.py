import time
import uuid
from contextlib import contextmanager
from sqlalchemy import (
    create_engine,
    String,
    Text,
    JSON,
    Float,
    Integer,
    UniqueConstraint,
    Index,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    expires: Mapped[float] = mapped_column(Float)


class Invitation(Base):
    __tablename__ = "invitations"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    email: Mapped[str] = mapped_column(String(254))
    expires: Mapped[float] = mapped_column(Float)
    used: Mapped[int] = mapped_column(Integer, default=0)


class Record(Base):
    """Versioned domain records, always addressed with org_id AND id/kind.

    JSON payload schemas are validated at API/service boundaries. Cross-record
    references are resolved using the same organization-scoped access function.
    """

    __tablename__ = "records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    org_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    work_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dedupe: Mapped[str | None] = mapped_column(String(200), nullable=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[float] = mapped_column(Float, default=time.time)
    __table_args__ = (
        UniqueConstraint("org_id", "kind", "dedupe"),
        Index("ix_record_scope", "org_id", "kind", "work_id"),
    )


settings.storage_dir.mkdir(parents=True, exist_ok=True)
if settings.database_url.startswith("sqlite"):
    from pathlib import Path

    Path(".data").mkdir(exist_ok=True)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 30}
    if settings.database_url.startswith("sqlite")
    else {},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@contextmanager
def transaction(org_id=None):
    with SessionLocal() as db:
        try:
            if engine.dialect.name == "sqlite":
                db.execute(text("BEGIN IMMEDIATE"))
            if org_id:
                db.execute(
                    select(Organization)
                    .where(Organization.id == org_id)
                    .with_for_update()
                ).scalar_one()
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def records(db, org, kind, work=None):
    q = select(Record).where(Record.org_id == org, Record.kind == kind)
    if work is not None:
        q = q.where(Record.work_id == work)
    return list(db.scalars(q.order_by(Record.created)))


def get(db, org, id, kind=None):
    from fastapi import HTTPException

    q = select(Record).where(Record.id == id, Record.org_id == org)
    if kind:
        q = q.where(Record.kind == kind)
    r = db.scalar(q)
    if not r:
        raise HTTPException(404, "Record not found in this workspace")
    return r


def add(db, org, kind, data, work=None, dedupe=None):
    r = Record(id=uid(), org_id=org, kind=kind, work_id=work, data=data, dedupe=dedupe)
    db.add(r)
    db.flush()
    return r


def update(record, **values):
    record.data = {**record.data, **values}


def public(record):
    return {
        "id": record.id,
        "created": record.created,
        **{
            k: v
            for k, v in record.data.items()
            if k not in ("storage_key", "route_token")
        },
    }
