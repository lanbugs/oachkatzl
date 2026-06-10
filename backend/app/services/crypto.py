from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


class CryptoError(Exception):
    """Raised when decryption fails (wrong key, corrupted data, etc.)."""


def _get_fernet() -> Fernet:
    key = os.environ.get("OACHKATZL_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError(
            "OACHKATZL_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    """Return Fernet-encrypted ciphertext as a unicode string."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt Fernet ciphertext. Raises CryptoError on failure."""
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception) as exc:
        raise CryptoError("Decryption failed") from exc


def generate_key() -> str:
    """Generate a new Fernet key (for initial setup)."""
    return Fernet.generate_key().decode()
