import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from .db import get_or_create_user, create_login_token, use_login_token
from .email_service import EmailService


def _get_auth_secret():
    secret = os.getenv("AUTH_SECRET")
    if not secret:
        raise RuntimeError("AUTH_SECRET is not set")
    return secret.encode("utf-8")


def _hash_token(token: str) -> str:
    secret = _get_auth_secret()
    digest = hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest


def _get_company_name():
    return os.getenv("DEFAULT_COMPANY_NAME", "Default Company")


def _extract_domain_from_email(email: str) -> str:
    """Extract domain from email address."""
    if "@" in email:
        return email.split("@")[1].lower()
    return None


def _get_company_name_from_domain(domain: str) -> str:
    """Generate a company name from domain (e.g., 'company.com' -> 'Company')"""
    if not domain:
        return _get_company_name()
    # Remove common TLDs and capitalize
    name = domain.split(".")[0]
    return name.capitalize()


def _get_app_base_url():
    return os.getenv("APP_BASE_URL", "http://localhost:8501")


def generate_login_token(email: str, ttl_minutes: int = 15):
    domain = _extract_domain_from_email(email)
    company_name = _get_company_name_from_domain(domain) if domain else _get_company_name()
    user = get_or_create_user(email=email, company_name=company_name, domain=domain)
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    create_login_token(user.id, token_hash, expires_at)
    return raw_token, user


def verify_login_token(raw_token: str):
    token_hash = _hash_token(raw_token)
    return use_login_token(token_hash)


def build_magic_link(raw_token: str):
    return f"{_get_app_base_url()}?login_token={raw_token}"


def send_magic_link(email: str, raw_token: str, sender: str, password: str):
    link = build_magic_link(raw_token)
    subject = "Your Mira login link"
    body = f"Click to login:\n\n{link}\n\nThis link expires in 15 minutes."
    # Support custom SMTP server/port via environment variables (defaults to Gmail)
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    mailer = EmailService(sender, password, server=smtp_server, port=smtp_port)
    return mailer.send_email(email, subject, body)
