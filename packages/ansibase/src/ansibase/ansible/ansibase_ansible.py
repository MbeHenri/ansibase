"""
Plugin d'inventaire dynamique ansibase
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
    name: ansibase_ansible
    plugin_type: inventory
    short_description: Inventaire dynamique PostgreSQL pour Ansible
    description:
      - Inventaire dynamique qui récupère les hôtes, groupes et variables depuis PostgreSQL
      - Supporte la hiérarchie de groupes
      - Gère le chiffrement des variables sensibles avec pgcrypto
      - Résout automatiquement les alias de variables
    options:
      host:
        description: Hôte PostgreSQL
        type: str
        default: localhost
      port:
        description: Port PostgreSQL
        type: int
        default: 5432
      database:
        description: Nom de la base de données
        type: str
        default: ansible_inventory
      user:
        description: Utilisateur PostgreSQL
        type: str
        default: ansible
      password:
        description: Mot de passe PostgreSQL
        type: str
        required: true
      encryption_key:
        description: Clé de chiffrement pour les variables sensibles
        type: str
        required: true
"""


from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.errors import AnsibleParserError
from ansible.inventory.data import InventoryData

from typing import Any, Dict

from ansibase.database import Database, DatabaseConfig
from ansibase.crypto import PgCrypto
from ansibase.builder import InventoryBuilder


class InventoryModule(BaseInventoryPlugin):

    NAME = "ansibase_ansible"

    def verify_file(self, path: str):
        """
        Vérifie que le fichier de configuration est valide
        """
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists
            # and is readable by current user
            if path.endswith(("ansibase.yaml", "ansibase.yml")):
                valid = True
        return valid

    def _populate_inventory(
        self, inventory: InventoryData, inventory_data: Dict[str, Any]
    ):
        """
        Peuple l'inventaire Ansible avec les données

        Args:
            inventory: Objet inventaire Ansible
            inventory_data: Données d'inventaire depuis ansibase
        """
        # Ajouter les groupes
        for group_name, group_data in inventory_data.items():
            if group_name == "_meta":
                continue

            # Créer le groupe
            inventory.add_group(group_name)

            # Ajouter les hôtes au groupe
            if "hosts" in group_data:
                for host_name in group_data["hosts"]:
                    # Créer l'hôte s'il n'existe pas
                    if host_name not in inventory.hosts:
                        inventory.add_host(host_name)

                    # Ajouter l'hôte au groupe
                    inventory.add_child(group_name, host_name)

            # Ajouter les groupes enfants
            if "children" in group_data:
                for child_name in group_data["children"]:
                    # Créer le groupe enfant s'il n'existe pas
                    if child_name not in inventory.groups:
                        inventory.add_group(child_name)

                    # Ajouter la relation parent-enfant
                    inventory.add_child(group_name, child_name)

            # Ajouter les variables de groupe
            if "vars" in group_data:
                for var_key, var_value in group_data["vars"].items():
                    inventory.set_variable(group_name, var_key, var_value)

        # Ajouter les variables d'hôtes (hostvars)
        if "_meta" in inventory_data and "hostvars" in inventory_data["_meta"]:
            for host_name, host_vars in inventory_data["_meta"]["hostvars"].items():
                # Créer l'hôte s'il n'existe pas encore
                if host_name not in inventory.hosts:
                    inventory.add_host(host_name)

                # Ajouter les variables
                for var_key, var_value in host_vars.items():
                    inventory.set_variable(host_name, var_key, var_value)

    def _generate_inventory(self, db_config: Dict[str, Any], encryption_key: str):
        """
        Génère l'inventaire depuis la base de données

        Args:
            db_config: Configuration de la base de données
            encryption_key: Clé de chiffrement

        Returns:
            dict: Inventaire au format Ansible
        """
        # Créer la connexion
        config = DatabaseConfig.from_dict(db_config)
        database = Database(config)
        crypto = PgCrypto(encryption_key)

        # Générer l'inventaire
        session = database.get_session()

        try:
            builder = InventoryBuilder(session, crypto)
            inventory_data = builder.build()
            return inventory_data
        finally:
            session.close()
            database.close()

    def parse(self, inventory, loader, path, cache):
        """
        Parse l'inventaire depuis PostgreSQL

        Args:
            inventory: Objet inventaire Ansible
            loader: Loader de données Ansible
            path: Chemin vers le fichier de configuration
            cache: Utiliser le cache ou non
        """
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        # Read the inventory YAML file
        self._read_config_data(path)

        db_config = None
        encryption_key = None
        try:
            db_config = {
                "host": self.get_option("host"),
                "port": self.get_option("port"),
                "database": self.get_option("database"),
                "user": self.get_option("user"),
                "password": self.get_option("password"),
            }
            encryption_key = self.get_option("encryption_key")

        except Exception as e:
            raise AnsibleParserError("All correct options required: {}".format(e))

        ansibase_data = self._generate_inventory(db_config, encryption_key)

        # Peupler l'inventaire Ansible
        self._populate_inventory(inventory, ansibase_data)
