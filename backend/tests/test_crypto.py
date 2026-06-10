"""Tests for crypto service."""
from app.services.crypto import encrypt, decrypt, generate_key


def test_encrypt_decrypt_roundtrip():
    plaintext = "super-secret-password"
    ciphertext = encrypt(plaintext)
    assert ciphertext != plaintext
    assert decrypt(ciphertext) == plaintext


def test_encrypt_empty_string():
    assert encrypt("") == ""
    assert decrypt("") == ""


def test_decrypt_invalid_raises_crypto_error():
    import pytest
    from app.services.crypto import CryptoError
    with pytest.raises(CryptoError):
        decrypt("not-valid-ciphertext")


def test_generate_key_is_valid_fernet_key():
    from cryptography.fernet import Fernet
    key = generate_key()
    # must be usable as a Fernet key
    f = Fernet(key.encode())
    assert f.decrypt(f.encrypt(b"test")) == b"test"


def test_different_plaintexts_give_different_ciphertexts():
    c1 = encrypt("secret1")
    c2 = encrypt("secret2")
    assert c1 != c2


def test_same_plaintext_gives_different_ciphertexts():
    """Fernet uses a random IV so same plaintext → different tokens."""
    c1 = encrypt("same")
    c2 = encrypt("same")
    assert c1 != c2
    assert decrypt(c1) == decrypt(c2) == "same"
