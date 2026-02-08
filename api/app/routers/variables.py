"""
Router pour la gestion du catalogue de variables et alias
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.pagination import PaginationParams
from app.dependencies.resolve import resolve_variable
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.variable import (
    AliasCreate,
    AliasResponse,
    VariableCreate,
    VariableResponse,
    VariableUpdate,
)
from app.services import variable as variable_service

router = APIRouter(prefix="/api/v1", tags=["variables"])


# ── Créer une variable


@router.post("/variables", response_model=VariableResponse, status_code=201)
def create_variable(
    # corps, parametres de la requete
    body: VariableCreate,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return variable_service.create_variable(
        db,
        var_key=body.var_key,
        description=body.description,
        is_sensitive=body.is_sensitive,
        var_type=body.var_type,
        default_value=body.default_value,
        validation_regex=body.validation_regex,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Lister les variables


@router.get("/variables", response_model=PaginatedResponse[VariableResponse])
def list_variables(
    # corps, parametres de la requete
    pagination: PaginationParams = Depends(),
    is_sensitive: Optional[bool] = Query(None),
    is_ansible_builtin: Optional[bool] = Query(None),
    var_type: Optional[str] = Query(None),
    # dependences / middlewares
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    variables, total = variable_service.list_variables(
        db,
        offset=pagination.offset,
        limit=pagination.limit,
        is_sensitive=is_sensitive,
        is_ansible_builtin=is_ansible_builtin,
        var_type=var_type,
    )
    return PaginatedResponse(
        items=variables,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=math.ceil(total / pagination.per_page) if total else 0,
    )


# ── Voir une variable


@router.get("/variables/{id_or_key}", response_model=VariableResponse)
def get_variable(
    id_or_key: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return resolve_variable(db, id_or_key)


# ── Modifier une variable


@router.put("/variables/{id_or_key}", response_model=VariableResponse)
def update_variable(
    # corps, parametres de la requete
    id_or_key: str,
    body: VariableUpdate,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    variable = resolve_variable(db, id_or_key)
    return variable_service.update_variable(
        db,
        variable=variable,
        description=body.description,
        is_sensitive=body.is_sensitive,
        var_type=body.var_type,
        default_value=body.default_value,
        validation_regex=body.validation_regex,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Supprimer une variable


@router.delete("/variables/{id_or_key}", status_code=204)
def delete_variable(
    # corps, parametres de la requete
    id_or_key: str,
    request: Request,
    force: bool = Query(False),
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    variable = resolve_variable(db, id_or_key)
    variable_service.delete_variable(
        db,
        variable=variable,
        force=force,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Créer un alias


@router.post(
    "/variables/{id_or_key}/aliases", response_model=AliasResponse, status_code=201
)
def create_alias(
    # corps, parametres de la requete
    id_or_key: str,
    body: AliasCreate,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alias_variable = resolve_variable(db, id_or_key)
    alias = variable_service.create_alias(
        db,
        alias_variable=alias_variable,
        source_variable_ref=body.source_variable,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )

    # on construit la reponse avec les noms de variables
    from app.models import Variable

    alias_var = db.get(Variable, alias.alias_var_id)
    source_var = db.get(Variable, alias.source_var_id)
    return AliasResponse(
        id=alias.id,
        alias_var_key=alias_var.var_key,
        source_var_key=source_var.var_key,
        description=alias.description,
        created_at=alias.created_at,
    )


# ── Lister les alias


@router.get("/variables/{id_or_key}/aliases", response_model=list[AliasResponse])
def list_aliases(
    id_or_key: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    variable = resolve_variable(db, id_or_key)
    return variable_service.list_aliases(db, variable=variable)


# ── Supprimer un alias


@router.delete("/variable-aliases/{alias_id}", status_code=204)
def delete_alias(
    # corps, parametres de la requete
    alias_id: int,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    variable_service.delete_alias(
        db,
        alias_id=alias_id,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
