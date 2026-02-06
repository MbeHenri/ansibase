#!/usr/bin/env python3
"""
Script d'inventaire dynamique ansibase
"""

import sys
import json
import argparse
from pathlib import Path
from configparser import ConfigParser

from ansibase.builder import InventoryBuilder
from ansibase.crypto import AnsibleCrypto
from ansibase.database import Database, DatabaseConfig

sys.path.insert(0, str(Path(__file__).parent))


def load_config(config_file: str = "ansibase.ini"):
    """Charge la configuration depuis un fichier INI"""
    config_path = Path(__file__).parent / config_file

    if not config_path.exists():
        raise FileNotFoundError(f"Fichier de configuration non trouvé: {config_path}")

    parser = ConfigParser()
    parser.read(config_path)

    # Convertir en dictionnaire
    config = {
        "database": {
            "host": parser.get("database", "host"),
            "port": parser.getint("database", "port"),
            "database": parser.get("database", "database"),
            "user": parser.get("database", "user"),
            "password": parser.get("database", "password"),
        },
        "encryption": {
            "key": parser.get("encryption", "key"),
        },
        "cache": {
            "enabled": parser.getboolean("cache", "enabled", fallback=True),
            "ttl": parser.getint("cache", "ttl", fallback=300),
        },
    }

    return config


def generate_inventory(config):
    """Génère l'inventaire complet"""
    db_config = DatabaseConfig.from_dict(config["database"])
    database = Database(db_config)
    crypto = AnsibleCrypto(config["encryption"]["key"])

    session = database.get_session()

    try:
        builder = InventoryBuilder(session, crypto)
        return builder.build()
    finally:
        session.close()


def get_host_vars(config, hostname):
    """Récupère les variables d'un hôte"""
    inventory = generate_inventory(config)
    return inventory["_meta"]["hostvars"].get(hostname, {})


def main():
    """Point d'entrée"""
    parser = argparse.ArgumentParser(
        description="Inventaire dynamique Ansible pour ansibase"
    )
    parser.add_argument("--list", action="store_true", help="Lister tout l'inventaire")
    parser.add_argument("--host", metavar="HOSTNAME", help="Variables d'un hôte")
    parser.add_argument(
        "--config", default="ansibase.ini", help="Fichier de configuration"
    )
    parser.add_argument("--pretty", action="store_true", help="JSON formaté")

    args = parser.parse_args()

    if not args.list and not args.host:
        parser.print_help()
        sys.exit(1)

    try:
        config = load_config(args.config)

        if args.list:
            result = generate_inventory(config)
        elif args.host:
            result = get_host_vars(config, args.host)

        indent = 2 if args.pretty else None
        print(json.dumps(result, indent=indent))

    except Exception as e:
        print(f"ERREUR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
