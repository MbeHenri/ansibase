"""
Schémas Pydantic pour les hôtes
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Schema pour les hôtes


# schema d'entree pour la creation
class HostCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


# schema d'entree pour la mise a jour
class HostUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# schema de sortie
class HostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Schema pour les groupes d'un hôte


# schema d'entree pour l'assignation a un groupe
class HostGroupAssign(BaseModel):
    group: str  # nom ou id


# ── Schema pour les variables d'un hôte


# schema d'entree pour l'assignation d'une variable
class HostVariableAssign(BaseModel):
    variable: str  # var_key ou id
    value: str


# schema d'entree pour l'assignation en masse
class HostVariableBulkAssign(BaseModel):
    variables: list[HostVariableAssign]


# schema de sortie pour une variable
class HostVariableResponse(BaseModel):
    var_key: str
    value: Optional[str]
    is_sensitive: bool


# schema de sortie pour l'assignation en masse
class HostVariableBulkResponse(BaseModel):
    assigned: list[HostVariableResponse]
    updated: list[HostVariableResponse]
    errors: list[dict]
