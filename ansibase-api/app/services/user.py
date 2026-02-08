"""
Service de gestion des utilisateurs et API Keys
"""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.utils import generate_key, hash_password, verify_password
from app.models.user import ApiKey, User
from app.services.audit import log_action
from app.services.crypto import encrypt_api_key, decrypt_api_key

# ── Endpoints pour les utilisateurs


def authenticate_user(
    db: Session,
    *,
    username: str,
    password: str,
    ip_address: Optional[str] = None,
) -> tuple[User, str]:
    """Authentifie un utilisateur par username/password.
    Retourne (User, clé API par défaut en clair).
    """

    # on recupere l'utilisateur
    user = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()

    # s'il n'existe pas, on renseigne que la requete n'a pas marche
    if not user or not verify_password(password, user.password_hash):
        log_action(
            db,
            user_id=None,
            action="AUTH_FAILED",
            resource_type="user",
            resource_id=username,
            details={"reason": "invalid_credentials"},
            ip_address=ip_address,
        )
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    # s'il est desactive on le signale egalement
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Utilisateur désactivé")

    # on recupere la cle d'API par defaut de l'utilisateur
    default_key = db.execute(
        select(ApiKey).where(
            ApiKey.user_id == user.id,
            ApiKey.name == "default",
            ApiKey.is_active == True,
        )
    ).scalar_one_or_none()

    if not default_key:
        raise HTTPException(
            status_code=500,
            detail="Clé API par défaut introuvable pour cet utilisateur",
        )

    # on dechiffre la cle d'API pour la retourner en clair
    decrypted_key = decrypt_api_key(db, default_key.key_value_encrypted)
    if not decrypted_key:
        raise HTTPException(
            status_code=500,
            detail="Impossible de déchiffrer la clé API par défaut",
        )

    # on renseigne dans les logs que tout est bon
    log_action(
        db,
        user_id=user.id,
        action="LOGIN",
        resource_type="user",
        resource_id=str(user.id),
        details={"username": username},
        ip_address=ip_address,
    )
    return user, decrypted_key


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    is_superuser: bool = False,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> tuple[User, str]:
    """Crée un nouvel utilisateur avec une clé API par défaut (sans expiration).
    Retourne (User, clé en clair).
    """

    # on verifie si l'utilisateur avec le username donne n'existe pas
    existing = db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Username '{username}' déjà utilisé"
        )

    # si non on le cree et on l'ajoute
    user = User(
        username=username,
        password_hash=hash_password(password),
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()

    # on genere une cle d'API par defaut sans expiration
    raw_key, key_hash = generate_key()
    default_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_value_encrypted=encrypt_api_key(db, raw_key),
        key_prefix=raw_key[:12],
        name="default",
    )
    db.add(default_key)
    db.flush()

    # on le renseigne dans les logs
    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="user",
        resource_id=str(user.id),
        details={"username": username, "is_superuser": is_superuser},
        ip_address=ip_address,
    )
    return user, raw_key


def list_users(
    db: Session, *, offset: int = 0, limit: int = 50
) -> tuple[list[User], int]:
    """Liste paginée des utilisateurs"""
    total = db.execute(select(func.count(User.id))).scalar_one()
    users = (
        db.execute(select(User).order_by(User.id).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return list(users), total


def get_user(db: Session, user: User) -> User:
    """Retourne un utilisateur (déjà résolu)"""
    return user


def update_user(
    db: Session,
    *,
    user: User,
    password: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_superuser: Optional[bool] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> User:
    """Met à jour un utilisateur"""

    # on identifie le changement qu'on souhaite appliquer
    changes = {}
    if password is not None:
        user.password_hash = hash_password(password)
        changes["password"] = "***changed***"
    if is_active is not None:
        user.is_active = is_active
        changes["is_active"] = is_active
    if is_superuser is not None:
        user.is_superuser = is_superuser
        changes["is_superuser"] = is_superuser

    # puis on l'applique
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        resource_type="user",
        resource_id=str(user.id),
        details=changes,
        ip_address=ip_address,
    )
    return user


def delete_user(
    db: Session,
    *,
    user: User,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Supprime un utilisateur"""
    user_id = user.id
    username = user.username
    db.delete(user)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="user",
        resource_id=str(user_id),
        details={"username": username},
        ip_address=ip_address,
    )


# ── Endpoints pour les API keys


def generate_api_key(
    db: Session,
    *,
    user: User,
    name: str,
    expires_at: Optional[datetime] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> tuple[ApiKey, str]:
    """Génère une API Key pour un utilisateur. Retourne (ApiKey, clé en clair)."""
    raw_key, key_hash = generate_key()

    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        key_value_encrypted=encrypt_api_key(db, raw_key),
        key_prefix=raw_key[:12],
        name=name,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="api_key",
        resource_id=str(api_key.id),
        details={"name": name, "user_id": user.id, "expires_at": str(expires_at)},
        ip_address=ip_address,
    )
    return api_key, raw_key


def list_api_keys(db: Session, *, user: User) -> list[dict]:
    """Liste les API Keys d'un utilisateur avec les valeurs dechiffrees"""
    keys = (
        db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user.id)
            .order_by(ApiKey.created_at.desc())
        )
        .scalars()
        .all()
    )
    result = []
    for key in keys:
        result.append(
            {
                "id": key.id,
                "key_value": "**************",  # La valeur de la clé n'est pas déchiffrée
                "key_prefix": key.key_prefix,
                "name": key.name,
                "expires_at": key.expires_at,
                "is_active": key.is_active,
                "created_at": key.created_at,
            }
        )
    return result


def revoke_api_key(
    db: Session,
    *,
    user: User,
    key_id: int,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Révoque une API Key"""
    api_key = db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    ).scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="Clé API introuvable")

    api_key.is_active = False
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="api_key",
        resource_id=str(key_id),
        details={"name": api_key.name, "user_id": user.id},
        ip_address=ip_address,
    )
