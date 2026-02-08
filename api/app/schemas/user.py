"""
Schémas Pydantic pour les utilisateurs et API Keys
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Schema pour les utilisateurs


# schema d'entree pour la creation
class UserCreate(BaseModel):
    username: str
    password: str
    is_superuser: bool = False


# schema d'entree pour la mise a jour
class UserUpdate(BaseModel):
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


# schema de sortie
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


# ── Schema pour l'authentification


# schema de requete du login
class LoginRequest(BaseModel):
    username: str
    password: str


# schema de reponse du login (affiche la cle d'API par defaut)
class LoginResponse(BaseModel):
    user: UserResponse
    api_key: str
    key_prefix: str


# ── Schema pour les API Keys


# schema d'entree pour la creation d'une API Key
class ApiKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None


# schema de sortie pour une API Key
class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_value: str
    key_prefix: str
    name: str
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
