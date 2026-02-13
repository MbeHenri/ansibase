#!/usr/bin/env python3
"""
Script d'inventaire dynamique ansibase
"""

import os
import sys
import json
import argparse

from ansibase.builder import InventoryBuilder
from ansibase.config import load_config
from ansibase.crypto import PgCrypto
from ansibase.database import Database, DatabaseConfig


def generate_inventory(config):
    """Génère l'inventaire complet"""
    db_config = DatabaseConfig.from_dict(config["database"])
    database = Database(db_config)
    crypto = PgCrypto(config["encryption"]["key"])

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
        "--config",
        default="ansibase.ini",
        help="Fichier de configuration INI ou YAML (defaut:ansibase.ini, env: ANSIBASE_CONFIG)",
    )
    parser.add_argument("--pretty", action="store_true", help="JSON formaté")

    args = parser.parse_args()

    if not args.list and not args.host:
        parser.print_help()
        sys.exit(1)

    try:
        config_file = args.config or os.environ.get("ANSIBASE_CONFIG", "ansibase.ini")
        config = load_config(config_file)

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
