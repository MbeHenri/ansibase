"""
Service de gestion du catalogue de variables et alias
"""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from sqlalchemy import delete as sql_delete

from app.models import (
    GroupRequiredVariable,
    GroupVariable,
    HostVariable,
    Variable,
    VariableAlias,
)
from app.dependencies.resolve import resolve_variable
from app.services.audit import log_action


# ── Endpoints pour les variables


def create_variable(
    db: Session,
    *,
    var_key: str,
    description: Optional[str] = None,
    is_sensitive: bool = False,
    var_type: str = "string",
    default_value: Optional[str] = None,
    validation_regex: Optional[str] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Variable:
    """Crée une nouvelle variable dans le catalogue"""

    # on verifie si la variable avec la cle donnee n'existe pas
    existing = db.execute(
        select(Variable).where(Variable.var_key == var_key)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Variable '{var_key}' existe déjà")

    # si non on la cree et on l'ajoute
    variable = Variable(
        var_key=var_key,
        description=description,
        is_sensitive=is_sensitive,
        var_type=var_type,
        default_value=default_value,
        validation_regex=validation_regex,
    )
    db.add(variable)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="variable",
        resource_id=str(variable.id),
        details={"var_key": var_key, "is_sensitive": is_sensitive},
        ip_address=ip_address,
    )
    return variable


def list_variables(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    is_sensitive: Optional[bool] = None,
    is_ansible_builtin: Optional[bool] = None,
    var_type: Optional[str] = None,
) -> tuple[list[Variable], int]:
    """Liste paginée du catalogue de variables avec filtres"""

    # on prepare les requetes avec les differents filtres
    stmt = select(Variable)
    count_stmt = select(func.count(Variable.id))

    if is_sensitive is not None:
        stmt = stmt.where(Variable.is_sensitive == is_sensitive)
        count_stmt = count_stmt.where(Variable.is_sensitive == is_sensitive)
    if is_ansible_builtin is not None:
        stmt = stmt.where(Variable.is_ansible_builtin == is_ansible_builtin)
        count_stmt = count_stmt.where(Variable.is_ansible_builtin == is_ansible_builtin)
    if var_type is not None:
        stmt = stmt.where(Variable.var_type == var_type)
        count_stmt = count_stmt.where(Variable.var_type == var_type)

    total = db.execute(count_stmt).scalar_one()
    variables = (
        db.execute(stmt.order_by(Variable.id).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return list(variables), total


def get_variable(db: Session, variable: Variable) -> Variable:
    """Retourne une variable (déjà résolue)"""
    return variable


def update_variable(
    db: Session,
    *,
    variable: Variable,
    description: Optional[str] = None,
    is_sensitive: Optional[bool] = None,
    var_type: Optional[str] = None,
    default_value: Optional[str] = None,
    validation_regex: Optional[str] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Variable:
    """Met à jour une variable du catalogue"""

    # on identifie le changement qu'on souhaite appliquer
    changes = {}

    # on interdit le changement de is_sensitive si des valeurs existent
    if is_sensitive is not None and is_sensitive != variable.is_sensitive:
        has_host_values = db.execute(
            select(func.count(HostVariable.id)).where(
                HostVariable.var_id == variable.id
            )
        ).scalar_one()
        has_group_values = db.execute(
            select(func.count(GroupVariable.id)).where(
                GroupVariable.var_id == variable.id
            )
        ).scalar_one()
        if has_host_values > 0 or has_group_values > 0:
            raise HTTPException(
                status_code=400,
                detail="Impossible de changer is_sensitive : des valeurs existent déjà",
            )
        variable.is_sensitive = is_sensitive
        changes["is_sensitive"] = is_sensitive

    if description is not None:
        variable.description = description
        changes["description"] = description
    if var_type is not None:
        variable.var_type = var_type
        changes["var_type"] = var_type
    if default_value is not None:
        variable.default_value = default_value
        changes["default_value"] = default_value
    if validation_regex is not None:
        variable.validation_regex = validation_regex
        changes["validation_regex"] = validation_regex

    # puis on l'applique
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        resource_type="variable",
        resource_id=str(variable.id),
        details=changes,
        ip_address=ip_address,
    )
    return variable


def delete_variable(
    db: Session,
    *,
    variable: Variable,
    force: bool = False,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Supprime une variable. Protection des builtins sauf force=True."""
    if variable.is_ansible_builtin and not force:
        raise HTTPException(
            status_code=403,
            detail="Variable builtin protégée. Utilisez ?force=true pour forcer.",
        )

    var_id = variable.id
    var_key = variable.var_key

    # on supprime les dependances avant la variable
    db.execute(sql_delete(HostVariable).where(HostVariable.var_id == var_id))
    db.execute(sql_delete(GroupVariable).where(GroupVariable.var_id == var_id))
    db.execute(
        sql_delete(GroupRequiredVariable).where(GroupRequiredVariable.var_id == var_id)
    )
    db.execute(
        sql_delete(VariableAlias).where(
            or_(
                VariableAlias.alias_var_id == var_id,
                VariableAlias.source_var_id == var_id,
            )
        )
    )

    db.delete(variable)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="variable",
        resource_id=str(var_id),
        details={"var_key": var_key, "force": force},
        ip_address=ip_address,
    )


# ── Endpoints pour les alias


def create_alias(
    db: Session,
    *,
    alias_variable: Variable,
    source_variable_ref: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> VariableAlias:
    """Crée un alias entre deux variables"""
    source_variable = resolve_variable(db, source_variable_ref)

    if alias_variable.id == source_variable.id:
        raise HTTPException(
            status_code=400, detail="Une variable ne peut pas être son propre alias"
        )

    # on verifie que l'alias n'existe pas deja
    existing = db.execute(
        select(VariableAlias).where(
            VariableAlias.alias_var_id == alias_variable.id,
            VariableAlias.source_var_id == source_variable.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Cet alias existe déjà")

    alias = VariableAlias(
        alias_var_id=alias_variable.id,
        source_var_id=source_variable.id,
    )
    db.add(alias)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="variable_alias",
        resource_id=str(alias.id),
        details={
            "alias_var_key": alias_variable.var_key,
            "source_var_key": source_variable.var_key,
        },
        ip_address=ip_address,
    )
    return alias


def list_aliases(db: Session, *, variable: Variable) -> list[dict]:
    """Liste les alias d'une variable (en tant que source ou alias)"""
    aliases = (
        db.execute(
            select(VariableAlias).where(
                or_(
                    VariableAlias.alias_var_id == variable.id,
                    VariableAlias.source_var_id == variable.id,
                )
            )
        )
        .scalars()
        .all()
    )

    result = []
    for a in aliases:
        alias_var = db.get(Variable, a.alias_var_id)
        source_var = db.get(Variable, a.source_var_id)
        result.append(
            {
                "id": a.id,
                "alias_var_key": (
                    alias_var.var_key if alias_var else str(a.alias_var_id)
                ),
                "source_var_key": (
                    source_var.var_key if source_var else str(a.source_var_id)
                ),
                "description": a.description,
                "created_at": a.created_at,
            }
        )
    return result


def delete_alias(
    db: Session,
    *,
    alias_id: int,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Supprime un alias"""
    alias = db.get(VariableAlias, alias_id)
    if not alias:
        raise HTTPException(status_code=404, detail="Alias introuvable")

    db.delete(alias)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="variable_alias",
        resource_id=str(alias_id),
        ip_address=ip_address,
    )
