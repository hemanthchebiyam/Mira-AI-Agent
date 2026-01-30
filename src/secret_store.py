import os
from cryptography.fernet import Fernet, InvalidToken

from .db import upsert_user_secret, get_user_secret, upsert_company_secret, get_company_secret


def _get_fernet():
    key = os.getenv("SECRETS_MASTER_KEY")
    if not key:
        raise RuntimeError("SECRETS_MASTER_KEY is not set")
    return Fernet(key)


def set_secret(user_id: str, key_name: str, plaintext: str):
    if plaintext is None:
        return None
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return upsert_user_secret(user_id, key_name, encrypted)


def get_secret(user_id: str, key_name: str):
    row = get_user_secret(user_id, key_name)
    if not row:
        return None
    fernet = _get_fernet()
    try:
        decrypted = fernet.decrypt(row.encrypted_value.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        return None


def set_company_secret(company_id: str, key_name: str, plaintext: str):
    """Set a company-level secret (encrypted)."""
    if plaintext is None:
        return None
    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return upsert_company_secret(company_id, key_name, encrypted)


def get_company_secret_value(company_id: str, key_name: str):
    """Get a company-level secret (decrypted)."""
    row = get_company_secret(company_id, key_name)
    if not row:
        return None
    fernet = _get_fernet()
    try:
        decrypted = fernet.decrypt(row.encrypted_value.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        return None
