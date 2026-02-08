"""
Schémas Pydantic pour les logs d'audit
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime
