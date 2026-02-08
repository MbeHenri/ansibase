"""
Dépendances d'authentification par API Key
Header attendu : Authorization: Bearer <api_key>
"""

from datetime import datetime

import bcrypt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import ApiKey, User

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    """Authentifie l'utilisateur via API Key (Bearer token)"""
    api_key_plain = credentials.credentials

    # Rechercher toutes les clés actives
    stmt = select(ApiKey).where(ApiKey.is_active == True)  # noqa: E712
    keys = db.execute(stmt).scalars().all()

    for key in keys:
        # Vérifier l'expiration
        if key.expires_at and key.expires_at < datetime.utcnow():
            continue

        # Comparer le hash bcrypt
        if bcrypt.checkpw(api_key_plain.encode("utf-8"), key.key_hash.encode("utf-8")):
            # Vérifier que l'utilisateur est actif
            user = db.get(User, key.user_id)
            if user and user.is_active:
                return user
            raise HTTPException(status_code=403, detail="Utilisateur désactivé")

    raise HTTPException(status_code=401, detail="Clé API invalide ou expirée")


def require_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Exige que l'utilisateur authentifié soit superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Accès réservé aux super-utilisateurs"
        )
    return current_user
