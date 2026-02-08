"""
Fonctions de résolution id_or_name pour les endpoints
Accepte un identifiant entier (ID) ou une chaîne (nom/clé)
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Host, Group, Variable, User


def resolve_host(db: Session, id_or_name: str) -> Host:
    """Résout un hôte par ID ou nom"""
    stmt = select(Host)
    if id_or_name.isdigit():
        stmt = stmt.where(Host.id == int(id_or_name))
    else:
        stmt = stmt.where(Host.name == id_or_name)
    host = db.execute(stmt).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=404, detail=f"Hôte '{id_or_name}' introuvable")
    return host


def resolve_group(db: Session, id_or_name: str) -> Group:
    """Résout un groupe par ID ou nom"""
    stmt = select(Group)
    if id_or_name.isdigit():
        stmt = stmt.where(Group.id == int(id_or_name))
    else:
        stmt = stmt.where(Group.name == id_or_name)
    group = db.execute(stmt).scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=404, detail=f"Groupe '{id_or_name}' introuvable"
        )
    return group


def resolve_variable(db: Session, id_or_key: str) -> Variable:
    """Résout une variable par ID ou var_key"""
    stmt = select(Variable)
    if id_or_key.isdigit():
        stmt = stmt.where(Variable.id == int(id_or_key))
    else:
        stmt = stmt.where(Variable.var_key == id_or_key)
    variable = db.execute(stmt).scalar_one_or_none()
    if not variable:
        raise HTTPException(
            status_code=404, detail=f"Variable '{id_or_key}' introuvable"
        )
    return variable


def resolve_user(db: Session, id_or_username: str) -> User:
    """Résout un utilisateur par ID ou username"""
    stmt = select(User)
    if id_or_username.isdigit():
        stmt = stmt.where(User.id == int(id_or_username))
    else:
        stmt = stmt.where(User.username == id_or_username)
    user = db.execute(stmt).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404, detail=f"Utilisateur '{id_or_username}' introuvable"
        )
    return user
