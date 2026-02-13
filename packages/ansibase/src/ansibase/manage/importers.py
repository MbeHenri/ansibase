"""Moteur d'import YAML pour hotes et groupes Ansible."""

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set

from sqlalchemy.orm import Session

from ansibase.crypto import PgCrypto
from ansibase.models import (
    Group,
    Host,
    HostGroup,
    HostVariable,
    GroupVariable,
    Variable,
)


KNOWN_SENSITIVE_KEYS: Set[str] = {
    "ansible_password",
    "ansible_become_password",
    "ansible_become_pass",
    "ansible_ssh_pass",
    "ansible_ssh_private_key_file",
}

KNOWN_BUILTIN_PREFIXES = ("ansible_",)


@dataclass
class ImportStats:
    """Compteurs d'import."""

    hosts_created: int = 0
    groups_created: int = 0
    variables_created: int = 0
    host_vars_set: int = 0
    group_vars_set: int = 0
    host_group_links: int = 0

    def summary(self) -> str:
        parts = []
        if self.hosts_created:
            parts.append(f"{self.hosts_created} hote(s) cree(s)")
        if self.groups_created:
            parts.append(f"{self.groups_created} groupe(s) cree(s)")
        if self.variables_created:
            parts.append(f"{self.variables_created} variable(s) creee(s)")
        if self.host_vars_set:
            parts.append(f"{self.host_vars_set} variable(s) d'hote assignee(s)")
        if self.group_vars_set:
            parts.append(f"{self.group_vars_set} variable(s) de groupe assignee(s)")
        if self.host_group_links:
            parts.append(f"{self.host_group_links} lien(s) hote-groupe cree(s)")
        return ", ".join(parts) if parts else "Aucune modification"


def normalize_value(value: Any) -> str:
    """Convertit une valeur YAML en chaine pour stockage."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def ensure_variable(
    session: Session,
    var_key: str,
    stats: ImportStats,
    extra_sensitive_keys: Optional[Set[str]] = None,
) -> Variable:
    """Upsert d'une variable dans le catalogue. Cree si inexistante."""
    var = session.query(Variable).filter(Variable.var_key == var_key).first()
    if var:
        return var

    sensitive_keys = KNOWN_SENSITIVE_KEYS
    if extra_sensitive_keys:
        sensitive_keys = sensitive_keys | extra_sensitive_keys

    is_sensitive = var_key in sensitive_keys
    is_builtin = any(var_key.startswith(p) for p in KNOWN_BUILTIN_PREFIXES)

    var = Variable(
        var_key=var_key,
        is_sensitive=is_sensitive,
        is_ansible_builtin=is_builtin,
    )
    session.add(var)
    session.flush()
    stats.variables_created += 1
    return var


def ensure_host(session: Session, hostname: str, stats: ImportStats) -> Host:
    """Upsert d'un hote. Cree si inexistant."""
    host = session.query(Host).filter(Host.name == hostname).first()
    if host:
        return host

    host = Host(name=hostname)
    session.add(host)
    session.flush()
    stats.hosts_created += 1
    return host


def ensure_group(
    session: Session,
    group_name: str,
    parent_id: Optional[int],
    stats: ImportStats,
) -> Group:
    """Upsert d'un groupe. Cree si inexistant, met a jour le parent si fourni."""
    grp = session.query(Group).filter(Group.name == group_name).first()
    if grp:
        if parent_id is not None and grp.parent_id != parent_id:
            grp.parent_id = parent_id
            session.flush()
        return grp

    grp = Group(name=group_name, parent_id=parent_id)
    session.add(grp)
    session.flush()
    stats.groups_created += 1
    return grp


def assign_host_variable(
    session: Session,
    crypto: PgCrypto,
    host: Host,
    variable: Variable,
    value: str,
    stats: ImportStats,
) -> None:
    """Upsert d'une variable d'hote avec chiffrement si sensible."""
    hv = (
        session.query(HostVariable)
        .filter(HostVariable.host_id == host.id, HostVariable.var_id == variable.id)
        .first()
    )

    if hv is None:
        hv = HostVariable(host_id=host.id, var_id=variable.id)
        session.add(hv)

    if variable.is_sensitive:
        hv.var_value_encrypted = crypto.encrypt_value(session, value)
        hv.var_value = None
    else:
        hv.var_value = value
        hv.var_value_encrypted = None

    session.flush()
    stats.host_vars_set += 1


def assign_group_variable(
    session: Session,
    crypto: PgCrypto,
    group: Group,
    variable: Variable,
    value: str,
    stats: ImportStats,
) -> None:
    """Upsert d'une variable de groupe avec chiffrement si sensible."""
    gv = (
        session.query(GroupVariable)
        .filter(GroupVariable.group_id == group.id, GroupVariable.var_id == variable.id)
        .first()
    )

    if gv is None:
        gv = GroupVariable(group_id=group.id, var_id=variable.id)
        session.add(gv)

    if variable.is_sensitive:
        gv.var_value_encrypted = crypto.encrypt_value(session, value)
        gv.var_value = None
    else:
        gv.var_value = value
        gv.var_value_encrypted = None

    session.flush()
    stats.group_vars_set += 1


def assign_host_to_group(
    session: Session, host: Host, group: Group, stats: ImportStats
) -> None:
    """Lien hote-groupe idempotent."""
    existing = (
        session.query(HostGroup)
        .filter(HostGroup.host_id == host.id, HostGroup.group_id == group.id)
        .first()
    )
    if existing:
        return

    hg = HostGroup(host_id=host.id, group_id=group.id)
    session.add(hg)
    session.flush()
    stats.host_group_links += 1


def import_host_vars(
    session: Session,
    crypto: PgCrypto,
    hostname: str,
    variables: Dict[str, Any],
    stats: ImportStats,
    extra_sensitive_keys: Optional[Set[str]] = None,
) -> Host:
    """Importe un hote et ses variables."""
    host = ensure_host(session, hostname, stats)

    for var_key, raw_value in variables.items():
        value = normalize_value(raw_value)
        variable = ensure_variable(session, var_key, stats, extra_sensitive_keys)
        assign_host_variable(session, crypto, host, variable, value, stats)

    return host


def import_group_recursive(
    session: Session,
    crypto: PgCrypto,
    group_name: str,
    group_data: Optional[Dict[str, Any]],
    parent_id: Optional[int],
    stats: ImportStats,
    extra_sensitive_keys: Optional[Set[str]] = None,
) -> None:
    """Import recursif d'un groupe au format inventaire Ansible.

    Traite : hosts (avec variables), vars, children (recursif).
    """
    grp = ensure_group(session, group_name, parent_id, stats)

    if not group_data or not isinstance(group_data, dict):
        return

    # Hotes du groupe
    hosts_data = group_data.get("hosts")
    if hosts_data and isinstance(hosts_data, dict):
        for hostname, host_vars in hosts_data.items():
            host = ensure_host(session, hostname, stats)
            assign_host_to_group(session, host, grp, stats)
            if host_vars and isinstance(host_vars, dict):
                for var_key, raw_value in host_vars.items():
                    value = normalize_value(raw_value)
                    variable = ensure_variable(
                        session, var_key, stats, extra_sensitive_keys
                    )
                    assign_host_variable(session, crypto, host, variable, value, stats)

    # Variables du groupe
    vars_data = group_data.get("vars")
    if vars_data and isinstance(vars_data, dict):
        for var_key, raw_value in vars_data.items():
            value = normalize_value(raw_value)
            variable = ensure_variable(session, var_key, stats, extra_sensitive_keys)
            assign_group_variable(session, crypto, grp, variable, value, stats)

    # Sous-groupes (recursif)
    children_data = group_data.get("children")
    if children_data and isinstance(children_data, dict):
        for child_name, child_data in children_data.items():
            import_group_recursive(
                session,
                crypto,
                child_name,
                child_data,
                grp.id,
                stats,
                extra_sensitive_keys,
            )
