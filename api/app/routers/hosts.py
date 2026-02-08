"""
Router pour la gestion des hôtes
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams
from app.dependencies.resolve import resolve_host
from app.models.user import User
from app.schemas.host import (
    HostCreate,
    HostGroupAssign,
    HostResponse,
    HostUpdate,
    HostVariableAssign,
    HostVariableBulkAssign,
    HostVariableBulkResponse,
    HostVariableResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.services import host as host_service

router = APIRouter(prefix="/api/v1/hosts", tags=["hosts"])


# ── Créer un hôte


@router.post("", response_model=HostResponse, status_code=201)
def create_host(
    # corps, parametres de la requete
    body: HostCreate,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return host_service.create_host(
        db,
        name=body.name,
        description=body.description,
        is_active=body.is_active,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Lister les hôtes


@router.get("", response_model=PaginatedResponse[HostResponse])
def list_hosts(
    # corps, parametres de la requete
    pagination: PaginationParams = Depends(),
    is_active: Optional[bool] = Query(None),
    group: Optional[str] = Query(None, description="Filtrer par groupe (nom ou id)"),
    search: Optional[str] = Query(None, description="Recherche par nom"),
    # dependences / middlewares
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    hosts, total = host_service.list_hosts(
        db,
        offset=pagination.offset,
        limit=pagination.limit,
        is_active=is_active,
        group_ref=group,
        search=search,
    )
    return PaginatedResponse(
        items=hosts,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=math.ceil(total / pagination.per_page) if total else 0,
    )


# ── Voir un hôte


@router.get("/{id_or_name}", response_model=HostResponse)
def get_host(
    id_or_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return resolve_host(db, id_or_name)


# ── Modifier un hôte


@router.put("/{id_or_name}", response_model=HostResponse)
def update_host(
    # corps, parametres de la requete
    id_or_name: str,
    body: HostUpdate,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    return host_service.update_host(
        db,
        host=host,
        name=body.name,
        description=body.description,
        is_active=body.is_active,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Supprimer un hôte


@router.delete("/{id_or_name}", status_code=204)
def delete_host(
    # corps, parametres de la requete
    id_or_name: str,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    host_service.delete_host(
        db,
        host=host,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Ajouter un hôte à un groupe


@router.post("/{id_or_name}/groups", status_code=201)
def add_to_group(
    # corps, parametres de la requete
    id_or_name: str,
    body: HostGroupAssign,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    return host_service.add_to_group(
        db,
        host=host,
        group_ref=body.group,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Retirer un hôte d'un groupe


@router.delete("/{id_or_name}/groups/{group_id_or_name}", status_code=204)
def remove_from_group(
    # corps, parametres de la requete
    id_or_name: str,
    group_id_or_name: str,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    host_service.remove_from_group(
        db,
        host=host,
        group_ref=group_id_or_name,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Lister les groupes d'un hôte


@router.get("/{id_or_name}/groups", response_model=list[str])
def list_host_groups(
    id_or_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    return host_service.list_host_groups(db, host=host)


# ── Affecter une variable à un hôte


@router.post(
    "/{id_or_name}/variables", response_model=HostVariableResponse, status_code=201
)
def assign_variable(
    # corps, parametres de la requete
    id_or_name: str,
    body: HostVariableAssign,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    return host_service.assign_variable(
        db,
        host=host,
        variable_ref=body.variable,
        value=body.value,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Définir plusieurs variables d'un hôte


@router.put(
    "/{id_or_name}/variables", response_model=HostVariableBulkResponse
)
def bulk_assign_variables(
    # corps, parametres de la requete
    id_or_name: str,
    body: HostVariableBulkAssign,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    return host_service.bulk_assign_variables(
        db,
        host=host,
        variables=[v.model_dump() for v in body.variables],
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Modifier la valeur d'une variable


@router.put(
    "/{id_or_name}/variables/{var_id_or_key}", response_model=HostVariableResponse
)
def update_variable(
    # corps, parametres de la requete
    id_or_name: str,
    var_id_or_key: str,
    body: HostVariableAssign,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    return host_service.update_variable(
        db,
        host=host,
        variable_ref=var_id_or_key,
        value=body.value,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Retirer une variable d'un hôte


@router.delete("/{id_or_name}/variables/{var_id_or_key}", status_code=204)
def remove_variable(
    # corps, parametres de la requete
    id_or_name: str,
    var_id_or_key: str,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    host_service.remove_variable(
        db,
        host=host,
        variable_ref=var_id_or_key,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Lister les variables d'un hôte


@router.get("/{id_or_name}/variables", response_model=list[HostVariableResponse])
def list_host_variables(
    # corps, parametres de la requete
    id_or_name: str,
    reveal: bool = Query(False, description="Révéler les valeurs sensibles"),
    # dependences / middlewares
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    host = resolve_host(db, id_or_name)
    return host_service.list_host_variables(db, host=host, reveal=reveal)
