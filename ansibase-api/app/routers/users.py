"""
Router pour la gestion des utilisateurs et API Keys
"""

import math

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user, require_superuser
from app.dependencies.pagination import PaginationParams
from app.dependencies.resolve import resolve_user
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.user import (
    ApiKeyCreate,
    ApiKeyResponse,
    LoginResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services import user as user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ── Créer un utilisateur


@router.post("", response_model=LoginResponse, status_code=201)
def create_user(
    body: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    user, raw_key = user_service.create_user(
        db,
        username=body.username,
        password=body.password,
        is_superuser=body.is_superuser,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return LoginResponse(
        user=UserResponse.model_validate(user),
        api_key=raw_key,
        key_prefix=raw_key[:12],
    )


# ── Lister les utilisateurs


@router.get("", response_model=PaginatedResponse[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_superuser),
    pagination: PaginationParams = Depends(),
):
    users, total = user_service.list_users(
        db, offset=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse(
        items=users,
        total=total,
        page=pagination.page,
        per_page=pagination.per_page,
        pages=math.ceil(total / pagination.per_page) if total else 0,
    )


# ── Voir un utilisateur


@router.get("/{id_or_username}", response_model=UserResponse)
def get_user(
    id_or_username: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    user = resolve_user(db, id_or_username)
    return user


# ── Modifier un utilisateur


@router.put("/{id_or_username}", response_model=UserResponse)
def update_user(
    id_or_username: str,
    body: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    user = resolve_user(db, id_or_username)
    updated = user_service.update_user(
        db,
        user=user,
        password=body.password,
        is_active=body.is_active,
        is_superuser=body.is_superuser,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return updated


# ── Supprimer un utilisateur


@router.delete("/{id_or_username}", status_code=204)
def delete_user(
    id_or_username: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    user = resolve_user(db, id_or_username)
    user_service.delete_user(
        db,
        user=user,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )


# ── Générer une API Key


@router.post(
    "/{id_or_username}/api-keys", response_model=ApiKeyResponse, status_code=201
)
def create_api_key(
    id_or_username: str,
    body: ApiKeyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = resolve_user(db, id_or_username)
    api_key, raw_key = user_service.generate_api_key(
        db,
        user=user,
        name=body.name,
        expires_at=body.expires_at,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return ApiKeyResponse(
        id=api_key.id,
        key_value=raw_key,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
    )


# ── Lister ses API Keys


@router.get("/{id_or_username}/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    id_or_username: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    user = resolve_user(db, id_or_username)
    return user_service.list_api_keys(db, user=user)


# ── Révoquer une API Key


@router.delete("/{id_or_username}/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    id_or_username: str,
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = resolve_user(db, id_or_username)
    user_service.revoke_api_key(
        db,
        user=user,
        key_id=key_id,
        actor_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
