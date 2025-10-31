"""
Encryption utilities for sensitive loan application data.

This module provides field-level encryption using Fernet (symmetric encryption).
Only the most sensitive fields are encrypted to balance security with performance.
"""

import logging

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Get the encryption key from Django settings.

    Returns:
        bytes: The encryption key.

    Raises:
        ValueError: If FIELD_ENCRYPTION_KEY is not set in settings.
    """
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if not key:
        msg_1 = "FIELD_ENCRYPTION_KEY not found in settings. "
        msg_2 = "Run: python manage.py generate_encryption_key"
        v_msg = msg_1 + msg_2
        raise ValueError(
            v_msg,
        )

    # Ensure key is bytes
    if isinstance(key, str):
        key = key.encode()

    return key


def encrypt_field(value: str | None) -> bytes | None:
    """
    Encrypt a field value using Fernet symmetric encryption.

    Args:
        value (str | None): The plaintext value to encrypt.

    Returns:
        bytes | None: The encrypted value as bytes (suitable for BinaryField),
        or None if input is empty.

    Example:
        >>> encrypted = encrypt_field("123-45-6789")
        >>> # Store in database BinaryField
    """
    if not value:
        return None

    key = get_encryption_key()
    fernet = Fernet(key)

    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)

    return fernet.encrypt(value.encode())


def decrypt_field(encrypted_value: bytes | None) -> str | None:
    """
    Decrypt a field value encrypted with Fernet.

    Args:
        encrypted_value (bytes | None): The encrypted value from the database.

    Returns:
        str | None: The decrypted plaintext value, or None if decryption fails.

    Example:
        >>> decrypted = decrypt_field(db_value)
        >>> print(decrypted)  # "123-45-6789"
    """
    if not encrypted_value:
        return None

    key = get_encryption_key()
    fernet = Fernet(key)

    try:
        decrypted = fernet.decrypt(encrypted_value)
        return decrypted.decode()
    except InvalidToken:
        logger.warning("Failed to decrypt field: Invalid encryption token.")
    except Exception:
        logger.exception("Unexpected error during field decryption")

    return None


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Returns:
        str: A base64-encoded encryption key.

    Example:
        >>> key = generate_encryption_key()
        >>> print(key)
        'xNjdG4yOHpwTjR6...'

    Note:
        Store this key securely in your environment variables or secrets manager.
        DO NOT commit it to version control.
    """
    return Fernet.generate_key().decode()
