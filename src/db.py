import os
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    DateTime,
    Text,
    Integer,
    ForeignKey,
    select,
    insert,
    update,
)


_engine = None
metadata = MetaData()


def utcnow():
    return datetime.now(timezone.utc)


def get_engine():
    global _engine
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    if _engine is None:
        _engine = create_engine(db_url, pool_pre_ping=True)
    return _engine


companies = Table(
    "companies",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(255), nullable=False, unique=True),
    Column("domain", String(255), nullable=True, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

users = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(255), nullable=False, unique=True),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("role", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

login_tokens = Table(
    "login_tokens",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("token_hash", String(64), nullable=False, index=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

documents = Table(
    "documents",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("filename", String(512), nullable=False),
    Column("path", Text, nullable=False),
    Column("size", Integer, nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("uploaded_at", DateTime(timezone=True), nullable=False),
)

user_secrets = Table(
    "user_secrets",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("key_name", String(64), nullable=False),
    Column("encrypted_value", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

company_secrets = Table(
    "company_secrets",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("key_name", String(64), nullable=False),
    Column("encrypted_value", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

audit_logs = Table(
    "audit_logs",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("company_id", String(36), ForeignKey("companies.id"), nullable=False),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("action", String(64), nullable=False),
    Column("doc_id", String(36), nullable=True),
    Column("meta_json", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


def init_db():
    engine = get_engine()
    metadata.create_all(engine)


def _new_id():
    return str(uuid.uuid4())


def get_or_create_company(name: str, domain: str = None):
    engine = get_engine()
    with engine.begin() as conn:
        # Try to find by domain first (if provided)
        if domain:
            row = conn.execute(select(companies).where(companies.c.domain == domain)).fetchone()
            if row:
                return row
        # Fall back to name lookup
        row = conn.execute(select(companies).where(companies.c.name == name)).fetchone()
        if row:
            # Update domain if it wasn't set before
            if domain and not row.domain:
                conn.execute(
                    update(companies)
                    .where(companies.c.id == row.id)
                    .values(domain=domain)
                )
                row = conn.execute(select(companies).where(companies.c.id == row.id)).fetchone()
            return row
        # Create new company
        company_id = _new_id()
        conn.execute(
            insert(companies).values(
                id=company_id,
                name=name,
                domain=domain,
                created_at=utcnow(),
            )
        )
        return conn.execute(select(companies).where(companies.c.id == company_id)).fetchone()


def get_company_by_domain(domain: str):
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(select(companies).where(companies.c.domain == domain)).fetchone()
        return row


def get_or_create_user(email: str, company_name: str, domain: str = None):
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(select(users).where(users.c.email == email)).fetchone()
        if row:
            return row
        company = get_or_create_company(company_name, domain=domain)
        existing_count = conn.execute(
            select(users.c.id).where(users.c.company_id == company.id)
        ).fetchall()
        role = "admin" if len(existing_count) == 0 else "member"
        user_id = _new_id()
        conn.execute(
            insert(users).values(
                id=user_id,
                email=email,
                company_id=company.id,
                role=role,
                created_at=utcnow(),
            )
        )
        return conn.execute(select(users).where(users.c.id == user_id)).fetchone()


def create_login_token(user_id: str, token_hash: str, expires_at):
    engine = get_engine()
    token_id = _new_id()
    with engine.begin() as conn:
        conn.execute(
            insert(login_tokens).values(
                id=token_id,
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                created_at=utcnow(),
            )
        )
    return token_id


def use_login_token(token_hash: str):
    engine = get_engine()
    with engine.begin() as conn:
        token_row = conn.execute(
            select(login_tokens).where(login_tokens.c.token_hash == token_hash)
        ).fetchone()
        if not token_row:
            return None
        if token_row.used_at is not None:
            return None
        if token_row.expires_at <= utcnow():
            return None
        conn.execute(
            update(login_tokens)
            .where(login_tokens.c.id == token_row.id)
            .values(used_at=utcnow())
        )
        user_row = conn.execute(select(users).where(users.c.id == token_row.user_id)).fetchone()
        return user_row


def insert_document(company_id, user_id, filename, path, size, sha256):
    engine = get_engine()
    doc_id = _new_id()
    with engine.begin() as conn:
        conn.execute(
            insert(documents).values(
                id=doc_id,
                company_id=company_id,
                user_id=user_id,
                filename=filename,
                path=path,
                size=size,
                sha256=sha256,
                uploaded_at=utcnow(),
            )
        )
    return doc_id


def insert_audit_log(company_id, user_id, action, doc_id=None, meta=None):
    engine = get_engine()
    log_id = _new_id()
    with engine.begin() as conn:
        conn.execute(
            insert(audit_logs).values(
                id=log_id,
                company_id=company_id,
                user_id=user_id,
                action=action,
                doc_id=doc_id,
                meta_json=json.dumps(meta or {}),
                created_at=utcnow(),
            )
        )
    return log_id


def upsert_user_secret(user_id, key_name, encrypted_value):
    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            select(user_secrets).where(
                (user_secrets.c.user_id == user_id)
                & (user_secrets.c.key_name == key_name)
            )
        ).fetchone()
        if existing:
            conn.execute(
                update(user_secrets)
                .where(user_secrets.c.id == existing.id)
                .values(encrypted_value=encrypted_value, updated_at=utcnow())
            )
            return existing.id
        secret_id = _new_id()
        conn.execute(
            insert(user_secrets).values(
                id=secret_id,
                user_id=user_id,
                key_name=key_name,
                encrypted_value=encrypted_value,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        return secret_id


def get_user_secret(user_id, key_name):
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            select(user_secrets).where(
                (user_secrets.c.user_id == user_id)
                & (user_secrets.c.key_name == key_name)
            )
        ).fetchone()
        return row


def upsert_company_secret(company_id, key_name, encrypted_value):
    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            select(company_secrets).where(
                (company_secrets.c.company_id == company_id)
                & (company_secrets.c.key_name == key_name)
            )
        ).fetchone()
        if existing:
            conn.execute(
                update(company_secrets)
                .where(company_secrets.c.id == existing.id)
                .values(encrypted_value=encrypted_value, updated_at=utcnow())
            )
            return existing.id
        secret_id = _new_id()
        conn.execute(
            insert(company_secrets).values(
                id=secret_id,
                company_id=company_id,
                key_name=key_name,
                encrypted_value=encrypted_value,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        return secret_id


def get_company_secret(company_id, key_name):
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            select(company_secrets).where(
                (company_secrets.c.company_id == company_id)
                & (company_secrets.c.key_name == key_name)
            )
        ).fetchone()
        return row
