"""
Module de chiffrement/déchiffrement pour ansibase
Gère les variables sensibles avec pgcrypto
"""

from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session


class PgCrypto:
    """Gestionnaire de chiffrement/déchiffrement pour variables sensibles"""

    def __init__(self, encryption_key: str) -> None:
        """
        Initialise le gestionnaire de crypto

        Args:
            encryption_key: Clé de chiffrement utilisée par pgcrypto
        """
        self.encryption_key: str = encryption_key

    def decrypt_value(self, session: Session, encrypted_value: bytes) -> Optional[str]:
        """
        Déchiffre une valeur chiffrée avec pgp_sym_decrypt

        Args:
            session: Session SQLAlchemy
            encrypted_value: Valeur chiffrée

        Returns:
            Valeur déchiffrée ou None en cas d'erreur
        """
        if not encrypted_value:
            return None

        try:
            result = session.execute(
                text("SELECT pgp_sym_decrypt(:encrypted, :key)"),
                {"encrypted": encrypted_value, "key": self.encryption_key},
            )
            row = result.fetchone()
            return row[0] if row else None
        except Exception as e:
            print(f"Erreur lors du déchiffrement: {e}")
            return None

    def encrypt_value(self, session: Session, plain_value: str) -> Optional[bytes]:
        """
        Chiffre une valeur avec pgp_sym_encrypt

        Args:
            session: Session SQLAlchemy
            plain_value: Valeur en clair

        Returns:
            Valeur chiffrée ou None en cas d'erreur
        """
        if not plain_value:
            return None

        try:
            result = session.execute(
                text("SELECT pgp_sym_encrypt(:plain, :key)"),
                {"plain": plain_value, "key": self.encryption_key},
            )
            row = result.fetchone()
            return row[0] if row else None
        except Exception as e:
            print(f"Erreur lors du chiffrement: {e}")
            return None
