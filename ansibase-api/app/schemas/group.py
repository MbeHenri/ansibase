"""
Schémas Pydantic pour les groupes
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Schema pour les groupes


# schema d'entree pour la creation
class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent: Optional[str] = None  # nom ou id du parent


# schema d'entree pour la mise a jour
class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent: Optional[str] = None


# schema de sortie
class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    parent_id: Optional[int]
    created_at: datetime
    updated_at: datetime


# schema de sortie detaille
class GroupDetailResponse(GroupResponse):
    parent_name: Optional[str] = None
    children: list[str] = []
    hosts: list[str] = []


# schema de sortie pour l'arborescence
class GroupTreeNode(BaseModel):
    name: str
    children: list["GroupTreeNode"] = []


# ── Schema pour les variables de groupe


# schema d'entree pour l'assignation d'une variable
class GroupVariableAssign(BaseModel):
    variable: str  # var_key ou id
    value: str


# schema d'entree pour l'assignation en masse
class GroupVariableBulkAssign(BaseModel):
    variables: list[GroupVariableAssign]


# schema de sortie pour une variable
class GroupVariableResponse(BaseModel):
    var_key: str
    value: Optional[str]
    is_sensitive: bool


# schema de sortie pour l'assignation en masse
class GroupVariableBulkResponse(BaseModel):
    assigned: list[GroupVariableResponse]
    updated: list[GroupVariableResponse]
    errors: list[dict]


# ── Schema pour les variables requises


# schema d'entree pour la definition d'une variable requise
class RequiredVariableCreate(BaseModel):
    variable: str  # var_key ou id
    is_required: bool = True
    override_default_value: Optional[str] = None


# schema de sortie pour une variable requise
class RequiredVariableResponse(BaseModel):
    id: int
    var_key: str
    is_required: bool
    override_default_value: Optional[str]
