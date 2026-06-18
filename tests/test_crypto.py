"""TDD for netbox_eol.crypto — framework-free symmetric encryption of the API key.

The key is encrypted at rest with a Fernet key derived from a provided secret
(Django SECRET_KEY in production). No Django here — the secret is passed in.
"""

from netbox_eol import crypto


def test_encrypt_then_decrypt_roundtrips():
    secret = "s" * 50
    token = crypto.encrypt("integration-key-1A2B", secret)
    assert token != "integration-key-1A2B"  # actually encrypted
    assert crypto.decrypt(token, secret) == "integration-key-1A2B"


def test_decrypt_with_wrong_secret_returns_empty():
    token = crypto.encrypt("k", "secret-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert crypto.decrypt(token, "secret-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb") == ""


def test_empty_values_roundtrip_to_empty():
    assert crypto.encrypt("", "s" * 40) == ""
    assert crypto.decrypt("", "s" * 40) == ""
