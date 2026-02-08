"""
Service de gestion des groupes
"""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Group,
    GroupRequiredVariable,
    GroupVariable,
    HostGroup,
    Variable,
)
from app.dependencies.resolve import resolve_group, resolve_variable
from app.services import crypto as crypto_service
from app.services.audit import log_action

PROTECTED_GROUPS = {"all", "ungrouped"}


# ── Endpoints pour les groupes


def create_group(
    db: Session,
    *,
    name: str,
    description: Optional[str] = None,
    parent_ref: Optional[str] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Group:
    """Crée un nouveau groupe"""

    # on verifie si le groupe avec le nom donne n'existe pas
    existing = db.execute(select(Group).where(Group.name == name)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Groupe '{name}' existe déjà")

    # on resout le parent si specifie
    parent_id = None
    if parent_ref:
        parent = resolve_group(db, parent_ref)
        parent_id = parent.id

    # on cree le groupe et on l'ajoute
    group = Group(name=name, description=description, parent_id=parent_id)
    db.add(group)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="group",
        resource_id=str(group.id),
        details={"name": name, "parent_id": parent_id},
        ip_address=ip_address,
    )
    return group


def list_groups(
    db: Session, *, offset: int = 0, limit: int = 50
) -> tuple[list[Group], int]:
    """Liste paginée des groupes"""
    total = db.execute(select(func.count(Group.id))).scalar_one()
    groups = (
        db.execute(select(Group).order_by(Group.id).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return list(groups), total


def get_group_tree(db: Session) -> list[dict]:
    """Retourne l'arborescence hiérarchique des groupes"""
    groups = db.execute(select(Group).order_by(Group.id)).scalars().all()

    def build_node(group: Group) -> dict:
        children = [g for g in groups if g.parent_id == group.id]
        return {
            "name": group.name,
            "children": [build_node(c) for c in children],
        }

    # on part de la racine "all" si elle existe
    root = next((g for g in groups if g.name == "all"), None)
    if root:
        return [build_node(root)]
    return [build_node(g) for g in groups if g.parent_id is None]


def get_group_detail(db: Session, group: Group) -> dict:
    """Détails d'un groupe : parent, enfants, hôtes directs"""

    # on recupere le nom du parent
    parent_name = None
    if group.parent_id:
        parent = db.get(Group, group.parent_id)
        parent_name = parent.name if parent else None

    # on recupere les enfants
    children = (
        db.execute(select(Group.name).where(Group.parent_id == group.id))
        .scalars()
        .all()
    )

    # on recupere les hotes directs
    from app.models import Host

    host_ids = (
        db.execute(select(HostGroup.host_id).where(HostGroup.group_id == group.id))
        .scalars()
        .all()
    )
    hosts = []
    for hid in host_ids:
        h = db.get(Host, hid)
        if h:
            hosts.append(h.name)

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "parent_id": group.parent_id,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "parent_name": parent_name,
        "children": sorted(children),
        "hosts": sorted(hosts),
    }


def update_group(
    db: Session,
    *,
    group: Group,
    name: Optional[str] = None,
    description: Optional[str] = None,
    parent_ref: Optional[str] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> Group:
    """Met à jour un groupe"""

    # on identifie le changement qu'on souhaite appliquer
    changes = {}

    if name is not None and name != group.name:
        if group.name in PROTECTED_GROUPS:
            raise HTTPException(
                status_code=400,
                detail=f"Le groupe '{group.name}' ne peut pas être renommé",
            )
        existing = db.execute(
            select(Group).where(Group.name == name)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail=f"Groupe '{name}' existe déjà")
        group.name = name
        changes["name"] = name

    if description is not None:
        group.description = description
        changes["description"] = description

    if parent_ref is not None:
        parent = resolve_group(db, parent_ref)
        group.parent_id = parent.id
        changes["parent_id"] = parent.id

    # puis on l'applique
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        resource_type="group",
        resource_id=str(group.id),
        details=changes,
        ip_address=ip_address,
    )
    return group


def delete_group(
    db: Session,
    *,
    group: Group,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Supprime un groupe. Interdit pour all et ungrouped."""
    if group.name in PROTECTED_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Le groupe '{group.name}' ne peut pas être supprimé",
        )

    group_id = group.id
    group_name = group.name

    # on supprime les dependances avant le groupe
    db.execute(sql_delete(HostGroup).where(HostGroup.group_id == group_id))
    db.execute(sql_delete(GroupVariable).where(GroupVariable.group_id == group_id))
    db.execute(
        sql_delete(GroupRequiredVariable).where(
            GroupRequiredVariable.group_id == group_id
        )
    )

    db.delete(group)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="group",
        resource_id=str(group_id),
        details={"name": group_name},
        ip_address=ip_address,
    )


# ── Hôtes d'un groupe


def list_group_hosts(
    db: Session, *, group: Group, inherited: bool = False
) -> list[str]:
    """Liste les hôtes d'un groupe (directs ou avec héritage enfants)"""
    from app.models import Host

    if not inherited:
        host_ids = (
            db.execute(select(HostGroup.host_id).where(HostGroup.group_id == group.id))
            .scalars()
            .all()
        )
        hosts = []
        for hid in host_ids:
            h = db.get(Host, hid)
            if h:
                hosts.append(h.name)
        return sorted(hosts)

    # avec heritage : on collecte recursivement les enfants
    def collect_hosts(grp_id: int) -> set[str]:
        result = set()
        host_ids = (
            db.execute(select(HostGroup.host_id).where(HostGroup.group_id == grp_id))
            .scalars()
            .all()
        )
        for hid in host_ids:
            h = db.get(Host, hid)
            if h:
                result.add(h.name)

        child_ids = (
            db.execute(select(Group.id).where(Group.parent_id == grp_id))
            .scalars()
            .all()
        )
        for cid in child_ids:
            result |= collect_hosts(cid)
        return result

    return sorted(collect_hosts(group.id))


# ── Variables de groupe


def assign_group_variable(
    db: Session,
    *,
    group: Group,
    variable_ref: str,
    value: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Affecte une variable à un groupe (chiffrement auto si sensible)"""
    variable = resolve_variable(db, variable_ref)

    # on verifie que la variable n'est pas deja assignee
    existing = db.execute(
        select(GroupVariable).where(
            GroupVariable.group_id == group.id, GroupVariable.var_id == variable.id
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Variable '{variable.var_key}' déjà assignée au groupe '{group.name}'",
        )

    # on cree l'assignation avec chiffrement si sensible
    gv = GroupVariable(group_id=group.id, var_id=variable.id)
    if variable.is_sensitive:
        gv.var_value_encrypted = crypto_service.encrypt(db, value)
    else:
        gv.var_value = value

    db.add(gv)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="group_variable",
        resource_id=str(gv.id),
        details={"group": group.name, "variable": variable.var_key},
        ip_address=ip_address,
    )
    return {
        "var_key": variable.var_key,
        "value": "****" if variable.is_sensitive else value,
        "is_sensitive": variable.is_sensitive,
    }


def bulk_assign_group_variables(
    db: Session,
    *,
    group: Group,
    variables: list[dict],
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Définit les valeurs de plusieurs variables pour un groupe (upsert)"""
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
            select(GroupVariable).where(
                GroupVariable.group_id == group.id, GroupVariable.var_id == variable.id
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
                resource_type="group_variable",
                resource_id=str(existing.id),
                details={"group": group.name, "variable": variable.var_key},
                ip_address=ip_address,
            )
            updated.append({
                "var_key": variable.var_key,
                "value": "****" if variable.is_sensitive else value,
                "is_sensitive": variable.is_sensitive,
            })
        else:
            # nouvelle assignation
            gv = GroupVariable(group_id=group.id, var_id=variable.id)
            if variable.is_sensitive:
                gv.var_value_encrypted = crypto_service.encrypt(db, value)
            else:
                gv.var_value = value

            db.add(gv)
            db.flush()

            log_action(
                db,
                user_id=actor_id,
                action="CREATE",
                resource_type="group_variable",
                resource_id=str(gv.id),
                details={"group": group.name, "variable": variable.var_key},
                ip_address=ip_address,
            )
            assigned.append({
                "var_key": variable.var_key,
                "value": "****" if variable.is_sensitive else value,
                "is_sensitive": variable.is_sensitive,
            })

    return {"assigned": assigned, "updated": updated, "errors": errors}


def update_group_variable(
    db: Session,
    *,
    group: Group,
    variable_ref: str,
    value: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Met à jour la valeur d'une variable de groupe"""
    variable = resolve_variable(db, variable_ref)

    # on verifie que la variable est bien assignee
    gv = db.execute(
        select(GroupVariable).where(
            GroupVariable.group_id == group.id, GroupVariable.var_id == variable.id
        )
    ).scalar_one_or_none()
    if not gv:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{variable.var_key}' non assignée au groupe '{group.name}'",
        )

    # on met a jour la valeur avec chiffrement si sensible
    if variable.is_sensitive:
        gv.var_value_encrypted = crypto_service.encrypt(db, value)
        gv.var_value = None
    else:
        gv.var_value = value
        gv.var_value_encrypted = None

    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="UPDATE",
        resource_type="group_variable",
        resource_id=str(gv.id),
        details={"group": group.name, "variable": variable.var_key},
        ip_address=ip_address,
    )
    return {
        "var_key": variable.var_key,
        "value": "****" if variable.is_sensitive else value,
        "is_sensitive": variable.is_sensitive,
    }


def remove_group_variable(
    db: Session,
    *,
    group: Group,
    variable_ref: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Retire une variable d'un groupe"""
    variable = resolve_variable(db, variable_ref)

    # on verifie que la variable est bien assignee
    gv = db.execute(
        select(GroupVariable).where(
            GroupVariable.group_id == group.id, GroupVariable.var_id == variable.id
        )
    ).scalar_one_or_none()
    if not gv:
        raise HTTPException(
            status_code=404,
            detail=f"Variable '{variable.var_key}' non assignée au groupe '{group.name}'",
        )

    db.delete(gv)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="group_variable",
        resource_id=str(gv.id),
        details={"group": group.name, "variable": variable.var_key},
        ip_address=ip_address,
    )


def list_group_variables(
    db: Session, *, group: Group, inherited: bool = False
) -> list[dict]:
    """Liste les variables d'un groupe (directes ou avec héritage parent)"""
    variables = {}

    if inherited:
        # on remonte la hierarchie des parents
        chain = []
        current = group
        while current:
            chain.append(current)
            current = db.get(Group, current.parent_id) if current.parent_id else None
        chain.reverse()  # du parent racine vers le groupe courant

        for grp in chain:
            gvs = (
                db.execute(
                    select(GroupVariable).where(GroupVariable.group_id == grp.id)
                )
                .scalars()
                .all()
            )
            for gv in gvs:
                var = db.get(Variable, gv.var_id)
                if var:
                    if var.is_sensitive and gv.var_value_encrypted:
                        val = crypto_service.decrypt(db, gv.var_value_encrypted)
                    else:
                        val = gv.var_value
                    variables[var.var_key] = {
                        "var_key": var.var_key,
                        "value": "****" if var.is_sensitive else val,
                        "is_sensitive": var.is_sensitive,
                    }
    else:
        gvs = (
            db.execute(select(GroupVariable).where(GroupVariable.group_id == group.id))
            .scalars()
            .all()
        )
        for gv in gvs:
            var = db.get(Variable, gv.var_id)
            if var:
                if var.is_sensitive and gv.var_value_encrypted:
                    val = crypto_service.decrypt(db, gv.var_value_encrypted)
                else:
                    val = gv.var_value
                variables[var.var_key] = {
                    "var_key": var.var_key,
                    "value": "****" if var.is_sensitive else val,
                    "is_sensitive": var.is_sensitive,
                }

    return list(variables.values())


# ── Variables requises


def add_required_variable(
    db: Session,
    *,
    group: Group,
    variable_ref: str,
    is_required: bool = True,
    override_default_value: Optional[str] = None,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> dict:
    """Ajoute une variable requise/optionnelle pour un groupe"""
    variable = resolve_variable(db, variable_ref)

    # on verifie que la variable requise n'est pas deja definie
    existing = db.execute(
        select(GroupRequiredVariable).where(
            GroupRequiredVariable.group_id == group.id,
            GroupRequiredVariable.var_id == variable.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Variable '{variable.var_key}' déjà définie comme requise pour '{group.name}'",
        )

    grv = GroupRequiredVariable(
        group_id=group.id,
        var_id=variable.id,
        is_required=is_required,
        override_default_value=override_default_value,
    )
    db.add(grv)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="CREATE",
        resource_type="group_required_variable",
        resource_id=str(grv.id),
        details={
            "group": group.name,
            "variable": variable.var_key,
            "is_required": is_required,
        },
        ip_address=ip_address,
    )
    return {
        "id": grv.id,
        "var_key": variable.var_key,
        "is_required": grv.is_required,
        "override_default_value": grv.override_default_value,
    }


def remove_required_variable(
    db: Session,
    *,
    group: Group,
    variable_ref: str,
    actor_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Retire une variable requise d'un groupe"""
    variable = resolve_variable(db, variable_ref)

    grv = db.execute(
        select(GroupRequiredVariable).where(
            GroupRequiredVariable.group_id == group.id,
            GroupRequiredVariable.var_id == variable.id,
        )
    ).scalar_one_or_none()
    if not grv:
        raise HTTPException(status_code=404, detail="Variable requise introuvable")

    db.delete(grv)
    db.flush()

    log_action(
        db,
        user_id=actor_id,
        action="DELETE",
        resource_type="group_required_variable",
        resource_id=str(grv.id),
        details={"group": group.name, "variable": variable.var_key},
        ip_address=ip_address,
    )


def list_required_variables(db: Session, *, group: Group) -> list[dict]:
    """Liste les variables requises/optionnelles d'un groupe"""
    grvs = (
        db.execute(
            select(GroupRequiredVariable).where(
                GroupRequiredVariable.group_id == group.id
            )
        )
        .scalars()
        .all()
    )
    result = []
    for grv in grvs:
        var = db.get(Variable, grv.var_id)
        result.append(
            {
                "id": grv.id,
                "var_key": var.var_key if var else str(grv.var_id),
                "is_required": grv.is_required,
                "override_default_value": grv.override_default_value,
            }
        )
    return result
