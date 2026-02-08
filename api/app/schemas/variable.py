"""
Schémas Pydantic pour les variables et alias
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Schema pour les variables


# schema d'entree pour la creation
class VariableCreate(BaseModel):
    var_key: str
    description: Optional[str] = None
    is_sensitive: bool = False
    var_type: str = "string"
    default_value: Optional[str] = None
    validation_regex: Optional[str] = None


# schema d'entree pour la mise a jour
class VariableUpdate(BaseModel):
    description: Optional[str] = None
    is_sensitive: Optional[bool] = None
    var_type: Optional[str] = None
    default_value: Optional[str] = None
    validation_regex: Optional[str] = None


# schema de sortie
class VariableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    var_key: str
    description: Optional[str]
    is_sensitive: bool
    var_type: str
    default_value: Optional[str]
    validation_regex: Optional[str]
    is_ansible_builtin: bool
    created_at: datetime
    updated_at: datetime


# ── Schema pour les alias


# schema d'entree pour la creation d'un alias
class AliasCreate(BaseModel):
    source_variable: str  # var_key ou id de la variable source


# schema de sortie pour un alias
class AliasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alias_var_key: str
    source_var_key: str
    description: Optional[str]
    created_at: datetime
