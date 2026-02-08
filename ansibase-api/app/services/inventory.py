"""
Service d'export d'inventaire Ansible
Réutilise directement app.builder.InventoryBuilder
"""

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.builder import InventoryBuilder
from app.crypto import PgCrypto
from app.models import Group

from app.config import settings


def build_inventory(db: Session) -> dict[str, Any]:
    """Construit l'inventaire Ansible complet via InventoryBuilder"""
    crypto = PgCrypto(settings.ANSIBLE_ENCRYPTION_KEY)
    builder = InventoryBuilder(db, crypto)
    return builder.build()


def get_host_vars(db: Session, hostname: str) -> dict[str, Any]:
    """Retourne les variables d'un hôte spécifique"""
    crypto = PgCrypto(settings.ANSIBLE_ENCRYPTION_KEY)
    builder = InventoryBuilder(db, crypto)
    inventory = builder.build()
    hostvars = builder.get_host_vars(hostname)
    if not hostvars and hostname not in inventory.get("_meta", {}).get("hostvars", {}):
        raise HTTPException(
            status_code=404, detail=f"Hôte '{hostname}' introuvable dans l'inventaire"
        )
    return hostvars


def build_graph(db: Session) -> list[dict]:
    """Construit l'arborescence des groupes (équivalent --graph)"""
    from sqlalchemy import select

    groups = db.execute(select(Group).order_by(Group.id)).scalars().all()

    def build_node(group: Group) -> dict:
        children = [g for g in groups if g.parent_id == group.id]
        node = {"name": group.name}
        if children:
            node["children"] = [build_node(c) for c in children]
        return node

    root = next((g for g in groups if g.name == "all"), None)
    if root:
        return [build_node(root)]
    return [build_node(g) for g in groups if g.parent_id is None]
