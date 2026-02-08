"""
Router pour la gestion des groupes
"""

import math

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams
from app.dependencies.resolve import resolve_group
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupDetailResponse,
    GroupResponse,
    GroupUpdate,
    GroupVariableAssign,
    GroupVariableBulkAssign,
    GroupVariableBulkResponse,
    GroupVariableResponse,
    RequiredVariableCreate,
    RequiredVariableResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.services import group as group_service

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


# ── Créer un groupe


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(
    # corps, parametres de la requete
    body: GroupCreate,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return group_service.create_group(
        db,
        name=body.name,
        description=body.description,
        parent_ref=body.parent,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Lister les groupes


@router.get("")
def list_groups(
    # corps, parametres de la requete
    pagination: PaginationParams = Depends(),
    tree: bool = Query(False, description="Vue arborescente"),
    # dependences / middlewares
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if tree:
        return group_service.get_group_tree(db)

    groups, total = group_service.list_groups(
        db, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse(
        items=[GroupResponse.model_validate(g) for g in groups],
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=math.ceil(total / pagination.per_page) if total else 0,
    )


# ── Avoir les details d'un groupe


@router.get("/{id_or_name}", response_model=GroupDetailResponse)
def get_group(
    id_or_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.get_group_detail(db, group)


# ── Modifier un groupe


@router.put("/{id_or_name}", response_model=GroupResponse)
def update_group(
    # corps, parametres de la requete
    id_or_name: str,
    body: GroupUpdate,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.update_group(
        db,
        group=group,
        name=body.name,
        description=body.description,
        parent_ref=body.parent,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Supprimer un groupe


@router.delete("/{id_or_name}", status_code=204)
def delete_group(
    # corps, parametres de la requete
    id_or_name: str,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    group_service.delete_group(
        db,
        group=group,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Lister les hôtes d'un groupe


@router.get("/{id_or_name}/hosts", response_model=list[str])
def list_group_hosts(
    # corps, parametres de la requete
    id_or_name: str,
    inherited: bool = Query(False),
    # dependences / middlewares
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.list_group_hosts(db, group=group, inherited=inherited)


# ── Affecter une variable à un groupe


@router.post(
    "/{id_or_name}/variables", response_model=GroupVariableResponse, status_code=201
)
def assign_group_variable(
    # corps, parametres de la requete
    id_or_name: str,
    body: GroupVariableAssign,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.assign_group_variable(
        db,
        group=group,
        variable_ref=body.variable,
        value=body.value,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Définir plusieurs variables d'un groupe


@router.put("/{id_or_name}/variables", response_model=GroupVariableBulkResponse)
def bulk_assign_group_variables(
    # corps, parametres de la requete
    id_or_name: str,
    body: GroupVariableBulkAssign,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.bulk_assign_group_variables(
        db,
        group=group,
        variables=[v.model_dump() for v in body.variables],
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Modifier une variable de groupe


@router.put(
    "/{id_or_name}/variables/{var_id_or_key}", response_model=GroupVariableResponse
)
def update_group_variable(
    # corps, parametres de la requete
    id_or_name: str,
    var_id_or_key: str,
    body: GroupVariableAssign,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.update_group_variable(
        db,
        group=group,
        variable_ref=var_id_or_key,
        value=body.value,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Retirer une variable d'un groupe


@router.delete("/{id_or_name}/variables/{var_id_or_key}", status_code=204)
def remove_group_variable(
    # corps, parametres de la requete
    id_or_name: str,
    var_id_or_key: str,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    group_service.remove_group_variable(
        db,
        group=group,
        variable_ref=var_id_or_key,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Lister les variables d'un groupe


@router.get("/{id_or_name}/variables", response_model=list[GroupVariableResponse])
def list_group_variables(
    # corps, parametres de la requete
    id_or_name: str,
    inherited: bool = Query(False),
    # dependences / middlewares
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.list_group_variables(db, group=group, inherited=inherited)


# ── Définir une variable requise


@router.post(
    "/{id_or_name}/required-variables",
    response_model=RequiredVariableResponse,
    status_code=201,
)
def add_required_variable(
    # corps, parametres de la requete
    id_or_name: str,
    body: RequiredVariableCreate,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.add_required_variable(
        db,
        group=group,
        variable_ref=body.variable,
        is_required=body.is_required,
        override_default_value=body.override_default_value,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Retirer une variable requise


@router.delete("/{id_or_name}/required-variables/{var_id_or_key}", status_code=204)
def remove_required_variable(
    # corps, parametres de la requete
    id_or_name: str,
    var_id_or_key: str,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    group_service.remove_required_variable(
        db,
        group=group,
        variable_ref=var_id_or_key,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Lister les variables requises


@router.get(
    "/{id_or_name}/required-variables",
    response_model=list[RequiredVariableResponse],
)
def list_required_variables(
    id_or_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    group = resolve_group(db, id_or_name)
    return group_service.list_required_variables(db, group=group)
