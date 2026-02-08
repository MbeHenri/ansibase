"""
Router d'authentification
Endpoint public : login par username/password
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import LoginRequest, LoginResponse, UserResponse
from app.services import user as user_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    # corps, parametres de la requete
    body: LoginRequest,
    request: Request,
    # dependences / middlewares
    db: Session = Depends(get_db),
):
    """Authentification par username/password. Retourne la clé API par défaut."""
    user, decrypted_key = user_service.authenticate_user(
        db,
        username=body.username,
        password=body.password,
        ip_address=request.client.host if request.client else None,
    )
    return LoginResponse(
        user=UserResponse.model_validate(user),
        api_key=decrypted_key,
        key_prefix=decrypted_key[:12],
    )
