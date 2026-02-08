"""
Module models pour ansibase API
Re-exporte les modèles du package core et les modèles spécifiques à l'API
"""

from ansibase.models import (
    Base,
    Host,
    Group,
    Variable,
    VariableAlias,
    HostGroup,
    HostVariable,
    GroupVariable,
    GroupRequiredVariable,
)
from .user import User, ApiKey
from .audit import AuditLog

__all__ = [
    # Base
    "Base",
    # Modèles principaux (core)
    "Host",
    "Group",
    "Variable",
    "VariableAlias",
    # Tables de liaison (core)
    "HostGroup",
    "HostVariable",
    "GroupVariable",
    "GroupRequiredVariable",
    # Utilisateurs et clés API
    "User",
    "ApiKey",
    "AuditLog",
]
