"""
Service de chiffrement — wrapper autour de app.crypto.PgCrypto
"""

from typing import Optional

from sqlalchemy.orm import Session

from ansibase.crypto import PgCrypto
from app.config import settings

# chiffrement des variables sensibles
_crypto = PgCrypto(settings.ANSIBLE_ENCRYPTION_KEY)

# chiffrement des cles d'API (cle configuree par l'administrateur)
_api_key_crypto = PgCrypto(settings.ANSIBASE_SECRET_KEY)


def encrypt(session: Session, value: str) -> Optional[bytes]:
    """Chiffre une valeur via pgcrypto"""
    return _crypto.encrypt_value(session, value)


def decrypt(session: Session, encrypted: bytes) -> Optional[str]:
    """Déchiffre une valeur via pgcrypto"""
    return _crypto.decrypt_value(session, encrypted)


def encrypt_api_key(session: Session, value: str) -> Optional[bytes]:
    """Chiffre une clé API via pgcrypto (clé de chiffrement dédiée)"""
    return _api_key_crypto.encrypt_value(session, value)


def decrypt_api_key(session: Session, encrypted: bytes) -> Optional[str]:
    """Déchiffre une clé API via pgcrypto (clé de chiffrement dédiée)"""
    return _api_key_crypto.decrypt_value(session, encrypted)
