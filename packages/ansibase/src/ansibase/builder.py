"""
Constructeur d'inventaire Ansible pour ansibase
Utilise une structure arborescente pour gérer la hiérarchie des groupes
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from .models import (
    Host,
    Group,
    Variable,
    VariableAlias,
    HostVariable,
    GroupVariable,
    HostGroup,
)
from .crypto import PgCrypto
from .graph import GroupTree


class InventoryBuilder:
    """
    Constructeur d'inventaire Ansible depuis la base de données
    Utilise une approche arborescente pour gérer les hiérarchies
    """

    def __init__(self, session: Session, crypto: PgCrypto) -> None:
        """
        Initialise le constructeur d'inventaire

        Args:
            session: Session SQLAlchemy
            crypto: Gestionnaire de chiffrement
        """
        self.session: Session = session
        self.crypto: PgCrypto = crypto
        self.tree: GroupTree = GroupTree()
        self.aliases: Dict[str, str] = {}
        self.inventory: Dict[str, Any] = {"_meta": {"hostvars": {}}}

    def load_aliases(self) -> None:
        """
        Charge tous les alias de variables depuis la base de données
        """
        alias_records = self.session.query(VariableAlias).all()

        for alias_record in alias_records:
            alias_var = (
                self.session.query(Variable)
                .filter_by(id=alias_record.alias_var_id)
                .first()
            )
            source_var = (
                self.session.query(Variable)
                .filter_by(id=alias_record.source_var_id)
                .first()
            )

            if alias_var and source_var:
                self.aliases[alias_var.var_key] = source_var.var_key

    def resolve_aliases(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Résout les alias de variables

        Args:
            variables: Dictionnaire de variables

        Returns:
            Dictionnaire avec alias résolus
        """
        resolved: Dict[str, Any] = variables.copy()

        for alias_key, source_key in self.aliases.items():
            # Si l'alias n'existe pas mais la source oui, créer l'alias
            if alias_key not in resolved and source_key in resolved:
                resolved[alias_key] = resolved[source_key]

        return resolved

    def build_group_tree(self) -> None:
        """
        Construit l'arbre des groupes depuis la base de données
        """
        # Récupérer tous les groupes
        groups = self.session.query(Group).all()

        # Première passe : créer tous les nœuds
        for group in groups:
            self.tree.add_group(
                group_id=group.id,
                name=group.name,
                description=group.description,
                parent_id=group.parent_id,
            )

        # Deuxième passe : charger les variables de chaque groupe
        for group in groups:
            node = self.tree.get_node(group.id)
            if node:
                node.variables = self.load_group_variables(group.id)

    def load_group_variables(self, group_id: int) -> Dict[str, Any]:
        """
        Charge les variables d'un groupe spécifique

        Args:
            group_id: ID du groupe

        Returns:
            Dictionnaire des variables
        """
        variables: Dict[str, Any] = {}

        group_vars = (
            self.session.query(GroupVariable).filter_by(group_id=group_id).all()
        )

        for gv in group_vars:
            variable = self.session.query(Variable).filter_by(id=gv.var_id).first()

            if not variable:
                continue

            # Déchiffrer si nécessaire
            if variable.is_sensitive and gv.var_value_encrypted:
                value = self.crypto.decrypt_value(self.session, gv.var_value_encrypted)
            else:
                value = gv.var_value

            variables[variable.var_key] = value

        return variables

    def load_hosts(self) -> None:
        """
        Charge tous les hôtes actifs et les assigne à leurs groupes
        """
        hosts = self.session.query(Host).filter_by(is_active=True).all()

        for host in hosts:
            # Récupérer les groupes de l'hôte via la table de liaison HostGroup
            host_group_records = (
                self.session.query(HostGroup).filter_by(host_id=host.id).all()
            )

            for hg in host_group_records:
                # Récupérer le groupe correspondant
                group = self.session.query(Group).filter_by(id=hg.group_id).first()
                if group:
                    node = self.tree.get_node(group.id)
                    if node:
                        node.hosts.add(host.name)

            # Charger les variables de l'hôte
            host_vars = self.load_host_variables(host.id)

            # Résoudre les alias
            host_vars = self.resolve_aliases(host_vars)

            # Stocker dans _meta.hostvars
            self.inventory["_meta"]["hostvars"][host.name] = host_vars

    def load_host_variables(self, host_id: int) -> Dict[str, Any]:
        """
        Charge les variables d'un hôte spécifique

        Args:
            host_id: ID de l'hôte

        Returns:
            Dictionnaire des variables
        """
        variables: Dict[str, Any] = {}

        host_vars = self.session.query(HostVariable).filter_by(host_id=host_id).all()

        for hv in host_vars:
            variable = self.session.query(Variable).filter_by(id=hv.var_id).first()

            if not variable:
                continue

            # Déchiffrer si nécessaire
            if variable.is_sensitive and hv.var_value_encrypted:
                value = self.crypto.decrypt_value(self.session, hv.var_value_encrypted)
            else:
                value = hv.var_value

            variables[variable.var_key] = value

        return variables

    def build_inventory_structure(self) -> None:
        """
        Construit la structure d'inventaire Ansible depuis l'arbre
        Parcours en profondeur pour construire la structure
        """
        # Parcourir l'arbre en post-order pour propager les hôtes
        for node in self.tree.traverse_postorder():
            group_name = node.name

            # Initialiser la structure du groupe
            self.inventory[group_name] = {}

            # Ajouter les hôtes directs (pas les enfants)
            if node.hosts:
                self.inventory[group_name]["hosts"] = sorted(list(node.hosts))

            # Ajouter les enfants
            if node.children:
                self.inventory[group_name]["children"] = sorted(
                    [child.name for child in node.children]
                )

            # Ajouter les variables
            if node.variables:
                resolved_vars = self.resolve_aliases(node.variables)
                if resolved_vars:
                    self.inventory[group_name]["vars"] = resolved_vars

    def cleanup_inventory(self) -> None:
        """
        Nettoie l'inventaire en supprimant les sections vides
        """
        for group_name in list(self.inventory.keys()):
            if group_name == "_meta":
                continue

            group = self.inventory[group_name]

            # Supprimer les clés vides
            if not group.get("hosts"):
                group.pop("hosts", None)

            if not group.get("children"):
                group.pop("children", None)

            if not group.get("vars"):
                group.pop("vars", None)

            # Supprimer le groupe s'il est complètement vide
            if not group:
                del self.inventory[group_name]

    def build(self) -> Dict[str, Any]:
        """
        Construit l'inventaire complet

        Returns:
            Inventaire au format Ansible
        """
        # 1. Charger les alias
        self.load_aliases()

        # 2. Construire l'arbre des groupes
        self.build_group_tree()

        # 3. Charger les hôtes
        self.load_hosts()

        # 4. Construire la structure d'inventaire
        self.build_inventory_structure()

        # 5. Nettoyer
        self.cleanup_inventory()

        return self.inventory

    def get_host_vars(self, hostname: str) -> Dict[str, Any]:
        """
        Récupère les variables d'un hôte spécifique

        Args:
            hostname: Nom de l'hôte

        Returns:
            Dictionnaire des variables de l'hôte
        """
        return self.inventory["_meta"]["hostvars"].get(hostname, {})
