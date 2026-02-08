"""
Module models pour ansibase
Exporte tous les modèles et définit les tables de liaison et relations Many-to-Many
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    LargeBinary,
)

from .base import Base
from .host import Host
from .group import Group
from .variable import Variable, VariableAlias


# ==============================================================================
# TABLES DE LIAISON ET RELATIONS MANY-TO-MANY
# ==============================================================================


class HostGroup(Base):
    """
    Table de liaison Many-to-Many entre Host et Group
    Représente l'appartenance d'un hôte à un groupe
    """

    __tablename__ = "ansibase_host_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_hosts.id", ondelete="CASCADE"), nullable=False
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_groups.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relations
    host: Mapped["Host"] = relationship("Host", backref="host_group_associations")
    group: Mapped["Group"] = relationship("Group", backref="host_group_associations")

    __table_args__ = (UniqueConstraint("host_id", "group_id"),)

    def __repr__(self) -> str:
        return f"<HostGroup(host_id={self.host_id}, group_id={self.group_id})>"


# ==============================================================================
# TABLES DE VARIABLES
# ==============================================================================


class HostVariable(Base):
    """
    Table Many-to-Many entre Host et Variable
    Stocke les valeurs des variables pour chaque hôte
    """

    __tablename__ = "ansibase_host_variables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_hosts.id", ondelete="CASCADE"), nullable=False
    )
    var_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_variables.id", ondelete="CASCADE"), nullable=False
    )
    var_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    var_value_encrypted: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relations
    host: Mapped["Host"] = relationship("Host", backref="host_variables")
    variable: Mapped["Variable"] = relationship(
        "Variable", backref="host_variable_values"
    )

    __table_args__ = (UniqueConstraint("host_id", "var_id"),)

    def __repr__(self) -> str:
        return f"<HostVariable(host_id={self.host_id}, var_id={self.var_id})>"


class GroupVariable(Base):
    """
    Table Many-to-Many entre Group et Variable
    Stocke les valeurs des variables pour chaque groupe
    """

    __tablename__ = "ansibase_group_variables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_groups.id", ondelete="CASCADE"), nullable=False
    )
    var_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_variables.id", ondelete="CASCADE"), nullable=False
    )
    var_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    var_value_encrypted: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relations
    group: Mapped["Group"] = relationship("Group", backref="group_variables")
    variable: Mapped["Variable"] = relationship(
        "Variable", backref="group_variable_values"
    )

    __table_args__ = (UniqueConstraint("group_id", "var_id"),)

    def __repr__(self) -> str:
        return f"<GroupVariable(group_id={self.group_id}, var_id={self.var_id})>"


class GroupRequiredVariable(Base):
    """
    Table définissant les variables requises/optionnelles pour un groupe
    Permet de spécifier quelles variables les hôtes d'un groupe doivent définir
    """

    __tablename__ = "ansibase_group_required_variables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_groups.id", ondelete="CASCADE"), nullable=False
    )
    var_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ansibase_variables.id", ondelete="CASCADE"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    override_default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relations
    group: Mapped["Group"] = relationship("Group", backref="required_variables")
    variable: Mapped["Variable"] = relationship(
        "Variable", backref="required_by_groups"
    )

    __table_args__ = (UniqueConstraint("group_id", "var_id"),)

    def __repr__(self) -> str:
        return f"<GroupRequiredVariable(group_id={self.group_id}, var_id={self.var_id}, required={self.is_required})>"


__all__ = [
    # Base
    "Base",
    # Modèles principaux
    "Host",
    "Group",
    "Variable",
    "VariableAlias",
    # Tables de liaison
    "HostGroup",
    # Variables
    "HostVariable",
    "GroupVariable",
    "GroupRequiredVariable",
]
