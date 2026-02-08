"""
Service de gestion des hôtes
"""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Group, Host, HostGroup, HostVariable, Variable
from app.dependencies.resolve import resolve_group, resolve_variable
from app.services import crypto as crypto_service
from app.services.audit import log_action


# ── Endpoints pour les hôtes


def create_host(
    db: Session,
    *,
    name: str,
    description: Optional[str] = None,
    is_active: bool = True,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Host:
    """Crée un nouvel hôte"""

    # on verifie si l'hote avec le nom donne n'existe pas
    existing = db.execute(select(Host).where(Host.name == name)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Hôte '{name}' existe déjà")

    # si non on le cree et on l'ajoute
    host = Host(name=name, description=description, is_active=is_active)
    db.add(host)
    db.flush()

    # on le renseigne dans les logs
    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="host",
        resource_id=str(host.id),
        details={"name": name},
        ip_address=ip_address,
    )
    return host


def list_hosts(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 50,
    is_active: Optional[bool] = None,
    group_ref: Optional[str] = None,
    search: Optional[str] = None,
) -> tuple[list[Host], int]:
    """Liste paginée des hôtes avec filtres"""

    # on prepare les requetes avec les differents filtres
    stmt = select(Host)
    count_stmt = select(func.count(Host.id))

    if is_active is not None:
        stmt = stmt.where(Host.is_active == is_active)
        count_stmt = count_stmt.where(Host.is_active == is_active)

    if search:
        stmt = stmt.where(Host.name.ilike(f"%{search}%"))
        count_stmt = count_stmt.where(Host.name.ilike(f"%{search}%"))

    if group_ref:
        # on resout le groupe pour filtrer
        group_stmt = select(Group)
        if group_ref.isdigit():
            group_stmt = group_stmt.where(Group.id == int(group_ref))
        else:
            group_stmt = group_stmt.where(Group.name == group_ref)
        group = db.execute(group_stmt).scalar_one_or_none()
        if group:
            host_ids_stmt = select(HostGroup.host_id).where(HostGroup.group_id == group.id)
            stmt = stmt.where(Host.id.in_(host_ids_stmt))
            count_stmt = count_stmt.where(Host.id.in_(host_ids_stmt))

    total = db.execute(count_stmt).scalar_one()
    hosts = (
        db.execute(stmt.order_by(Host.id).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return list(hosts), total


def update_host(
    db: Session,
    *,
    host: Host,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Host:
    """Met à jour un hôte"""

    # on identifie le changement qu'on souhaite appliquer
    changes = {}
    if name is not None and name != host.name:
        existing = db.execute(select(Host).where(Host.name == name)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail=f"Hôte '{name}' existe déjà")
        host.name = name
        changes["name"] = name
    if description is not None:
        host.description = description
        changes["description"] = description
    if is_active is not None:
        host.is_active = is_active
        changes["is_active"] = is_active

    # puis on l'applique
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        resource_type="host",
        resource_id=str(host.id),
        details=changes,
        ip_address=ip_address,
    )
    return host


def delete_host(
    db: Session,
    *,
    host: Host,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Supprime un hôte (cascade)"""
    host_id = host.id
    host_name = host.name

    # on supprime les dependances avant l'hote
    db.execute(sql_delete(HostGroup).where(HostGroup.host_id == host_id))
    db.execute(sql_delete(HostVariable).where(HostVariable.host_id == host_id))
    db.delete(host)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="host",
        resource_id=str(host_id),
        details={"name": host_name},
        ip_address=ip_address,
    )


# ── Groupes d'un hôte


def add_to_group(
    db: Session,
    *,
    host: Host,
    group_ref: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Ajoute un hôte à un groupe"""
    group = resolve_group(db, group_ref)

    # on verifie que l'hote n'est pas deja dans le groupe
    existing = db.execute(
        select(HostGroup).where(
            HostGroup.host_id == host.id, HostGroup.group_id == group.id
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Hôte '{host.name}' déjà dans le groupe '{group.name}'",
        )

    # si non on l'ajoute
    hg = HostGroup(host_id=host.id, group_id=group.id)
    db.add(hg)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="host_group",
        resource_id=str(hg.id),
        details={"host": host.name, "group": group.name},
        ip_address=ip_address,
    )
    return {"host": host.name, "group": group.name}


def remove_from_group(
    db: Session,
    *,
    host: Host,
    group_ref: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Retire un hôte d'un groupe"""
    group = resolve_group(db, group_ref)

    # on verifie que l'hote est bien dans le groupe
    hg = db.execute(
        select(HostGroup).where(
            HostGroup.host_id == host.id, HostGroup.group_id == group.id
        )
    ).scalar_one_or_none()
    if not hg:
        raise HTTPException(
            status_code=404,
            detail=f"Hôte '{host.name}' n'est pas dans le groupe '{group.name}'",
        )

    db.delete(hg)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="host_group",
        details={"host": host.name, "group": group.name},
        ip_address=ip_address,
    )


def list_host_groups(db: Session, *, host: Host) -> list[str]:
    """Liste les groupes d'un hôte"""
    group_ids = (
        db.execute(select(HostGroup.group_id).where(HostGroup.host_id == host.id))
        .scalars()
        .all()
    )
    groups = []
    for gid in group_ids:
        g = db.get(Group, gid)
        if g:
            groups.append(g.name)
    return sorted(groups)


# ── Variables d'un hôte


def assign_variable(
    db: Session,
    *,
    host: Host,
    variable_ref: str,
    value: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Affecte une variable à un hôte (chiffrement auto si sensible)"""
    variable = resolve_variable(db, variable_ref)

    # on verifie que la variable n'est pas deja assignee
    existing = db.execute(
        select(HostVariable).where(
            HostVariable.host_id == host.id, HostVariable.var_id == variable.id
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Variable '{variable.var_key}' déjà assignée à l'hôte '{host.name}'",
        )

    # on cree l'assignation avec chiffrement si sensible
    hv = HostVariable(host_id=host.id, var_id=variable.id)
    if variable.is_sensitive:
        hv.var_value_encrypted = crypto_service.encrypt(db, value)
    else:
        hv.var_value = value

    db.add(hv)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="host_variable",
        resource_id=str(hv.id),
        details={"host": host.name, "variable": variable.var_key},
        ip_address=ip_address,
    )
    return {
        "var_key": variable.var_key,
        "value": "****" if variable.is_sensitive else value,
        "is_sensitive": variable.is_sensitive,
    }


def update_variable(
    db: Session,
    *,
    host: Host,
    variable_ref: str,
    value: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Met à jour la valeur d'une variable d'hôte"""
    variable = resolve_variable(db, variable_ref)

    # on verifie que la variable est bien assignee
    hv = db.execute(
        select(HostVariable).where(
            HostVariable.host_id == host.id, HostVariable.var_id == variable.id
        )
    ).scalar_one_or_none()
    if not hv:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{variable.var_key}' non assignée à l'hôte '{host.name}'",
        )

    # on met a jour la valeur avec chiffrement si sensible
    if variable.is_sensitive:
        hv.var_value_encrypted = crypto_service.encrypt(db, value)
        hv.var_value = None
    else:
        hv.var_value = value
        hv.var_value_encrypted = None

    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        resource_type="host_variable",
        resource_id=str(hv.id),
        details={"host": host.name, "variable": variable.var_key},
        ip_address=ip_address,
    )
    return {
        "var_key": variable.var_key,
        "value": "****" if variable.is_sensitive else value,
        "is_sensitive": variable.is_sensitive,
    }


def remove_variable(
    db: Session,
    *,
    host: Host,
    variable_ref: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Retire une variable d'un hôte"""
    variable = resolve_variable(db, variable_ref)

    # on verifie que la variable est bien assignee
    hv = db.execute(
        select(HostVariable).where(
            HostVariable.host_id == host.id, HostVariable.var_id == variable.id
        )
    ).scalar_one_or_none()
    if not hv:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{variable.var_key}' non assignée à l'hôte '{host.name}'",
        )

    db.delete(hv)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="host_variable",
        details={"host": host.name, "variable": variable.var_key},
        ip_address=ip_address,
    )


def bulk_assign_variables(
    db: Session,
    *,
    host: Host,
    variables: list[dict],
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Définit les valeurs de plusieurs variables pour un hôte (upsert)"""
    assigned = []
    updated = []
    errors = []

    for item in variables:
        variable_ref = item["variable"]
        value = item["value"]

        # on resout la variable, si introuvable on l'ajoute aux erreurs
        try:
            variable = resolve_variable(db, variable_ref)
        except HTTPException:
            errors.append({
                "variable": variable_ref,
                "detail": f"Variable '{variable_ref}' introuvable",
            })
            continue

        # on verifie si la variable est deja assignee
        existing = db.execute(
            select(HostVariable).where(
                HostVariable.host_id == host.id, HostVariable.var_id == variable.id
            )
        ).scalar_one_or_none()

        if existing:
            # mise a jour de la valeur existante
            if variable.is_sensitive:
                existing.var_value_encrypted = crypto_service.encrypt(db, value)
                existing.var_value = None
            else:
                existing.var_value = value
                existing.var_value_encrypted = None
            db.flush()

            log_action(
                db,
                user_id=actor_id,
                action="UPDATE",
                resource_type="host_variable",
                resource_id=str(existing.id),
                details={"host": host.name, "variable": variable.var_key},
                ip_address=ip_address,
            )
            updated.append({
                "var_key": variable.var_key,
                "value": "****" if variable.is_sensitive else value,
                "is_sensitive": variable.is_sensitive,
            })
        else:
            # nouvelle assignation
            hv = HostVariable(host_id=host.id, var_id=variable.id)
            if variable.is_sensitive:
                hv.var_value_encrypted = crypto_service.encrypt(db, value)
            else:
                hv.var_value = value

            db.add(hv)
            db.flush()

            log_action(
                db,
                user_id=actor_id,
                action="CREATE",
                resource_type="host_variable",
                resource_id=str(hv.id),
                details={"host": host.name, "variable": variable.var_key},
                ip_address=ip_address,
            )
            assigned.append({
                "var_key": variable.var_key,
                "value": "****" if variable.is_sensitive else value,
                "is_sensitive": variable.is_sensitive,
            })

    return {"assigned": assigned, "updated": updated, "errors": errors}


def list_host_variables(
    db: Session, *, host: Host, reveal: bool = False
) -> list[dict]:
    """Liste les variables d'un hôte (sensibles masquées sauf reveal=true)"""
    hvs = (
        db.execute(select(HostVariable).where(HostVariable.host_id == host.id))
        .scalars()
        .all()
    )
    result = []
    for hv in hvs:
        var = db.get(Variable, hv.var_id)
        if not var:
            continue

        # on dechiffre si sensible et reveal=true
        if var.is_sensitive:
            if reveal and hv.var_value_encrypted:
                val = crypto_service.decrypt(db, hv.var_value_encrypted)
            else:
                val = "****"
        else:
            val = hv.var_value

        result.append({
            "var_key": var.var_key,
            "value": val,
            "is_sensitive": var.is_sensitive,
        })
    return result
