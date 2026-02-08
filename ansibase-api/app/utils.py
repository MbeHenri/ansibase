"""
Utilitaires pour le projet Ansibase API
"""

import bcrypt
import secrets


def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def generate_key(length: int = 48) -> tuple[str, str]:
    """Génère une clé API et son hash"""
    raw_key = secrets.token_urlsafe(length)
    key_hash = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    return raw_key, key_hash
