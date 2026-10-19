"""
Fernet-based encryption/decryption for OAuth refresh tokens.

Tokens are stored encrypted at rest in users.google_oauth_token_encrypted.
The symmetric key is read from the FERNET_KEY environment variable — it must
NEVER be hardcoded or committed.

Generating a key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging
import os

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_raw_key = os.getenv("FERNET_KEY")
if not _raw_key:
    logger.warning(
        "FERNET_KEY environment variable is not set — auto-generating temporary key for startup."
    )
    _raw_key = Fernet.generate_key().decode()

_fernet = Fernet(_raw_key.encode())


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a plaintext string (e.g. an OAuth refresh token) and return
    the base64-encoded ciphertext as a str.

    Args:
        plaintext: The secret string to encrypt.

    Returns:
        Base64-encoded Fernet token (safe to store in the DB).

    Raises:
        ValueError: If plaintext is empty.
    """
    if not plaintext:
        raise ValueError("Cannot encrypt an empty string")
    ciphertext_bytes = _fernet.encrypt(plaintext.encode("utf-8"))
    return ciphertext_bytes.decode("utf-8")


def decrypt_token(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted ciphertext back to plaintext.

    Args:
        ciphertext: Base64-encoded Fernet token (as stored in the DB).

    Returns:
        Original plaintext string.

    Raises:
        ValueError: If decryption fails (wrong key, tampered ciphertext).
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt an empty string")
    try:
        plaintext_bytes = _fernet.decrypt(ciphertext.encode("utf-8"))
        return plaintext_bytes.decode("utf-8")
    except InvalidToken as exc:
        logger.error("Token decryption failed — key mismatch or corrupted ciphertext")
        raise ValueError("Decryption failed: invalid token or wrong key") from exc
