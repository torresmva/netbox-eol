"""Symmetric encryption for the API key at rest (framework-free).

A Fernet key is derived from a provided secret (Django SECRET_KEY in production)
so the ciphertext is recoverable only with that secret. Documented trade-off:
anyone with the DB and SECRET_KEY can recover the key.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _fernet(secret):
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt(plaintext, secret):
    if not plaintext:
        return ""
    return _fernet(secret).encrypt(plaintext.encode()).decode()


def decrypt(token, secret):
    if not token:
        return ""
    try:
        return _fernet(secret).decrypt(token.encode()).decode()
    except InvalidToken:
        return ""
