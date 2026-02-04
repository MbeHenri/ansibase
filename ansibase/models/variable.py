"""
Modèles SQLAlchemy pour les variables
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Variable(Base):
    """Modèle pour la table ansibase_variables"""

    __tablename__ = "ansibase_variables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    var_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    var_type: Mapped[str] = mapped_column(String(50), default="string", nullable=False)
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_regex: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_ansible_builtin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Variable(id={self.id}, key='{self.var_key}', sensitive={self.is_sensitive})>"


class VariableAlias(Base):
    """Modèle pour la table ansibase_variable_aliases"""

    __tablename__ = "ansibase_variable_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias_var_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_variables.id", ondelete="CASCADE"), nullable=False
    )
    source_var_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_variables.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("alias_var_id", "source_var_id"),
        CheckConstraint("alias_var_id != source_var_id"),
    )

    def __repr__(self) -> str:
        return f"<VariableAlias(alias_id={self.alias_var_id}, source_id={self.source_var_id})>"
