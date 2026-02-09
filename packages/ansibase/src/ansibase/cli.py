"""CLI ansibase-db : gestion des migrations de base de donnees"""

import sys
import argparse

from ansibase.config import load_config


def main():
    # Parent parser pour les options communes a toutes les sous-commandes
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--config",
        default="ansibase.ini",
        help="Fichier de configuration INI ou YML (defaut: ansibase.ini)",
    )

    parser = argparse.ArgumentParser(
        description="Gestion du schema de base de donnees ansibase",
        parents=[parent],
    )

    sub = parser.add_subparsers(dest="command")

    # Sous-commandes
    up = sub.add_parser("upgrade", parents=[parent], help="Appliquer les migrations")
    up.add_argument("--revision", default="head", help="Revision cible (defaut: head)")

    down = sub.add_parser("downgrade", parents=[parent], help="Annuler des migrations")
    down.add_argument("--revision", required=True, help="Revision cible")

    sub.add_parser("current", parents=[parent], help="Afficher la revision courante")
    sub.add_parser("history", parents=[parent], help="Afficher l'historique des migrations")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Charger la config et construire l'URL
    config = load_config(args.config)
    db = config["database"]
    url = (
        f"postgresql://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['database']}"
    )

    # Import lazy d'Alembic
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
    except ImportError:
        print(
            "ERREUR: alembic n'est pas installe.\n"
            "Installez avec : pip install ansibase[db]",
            file=sys.stderr,
        )
        sys.exit(1)

    from ansibase.migrations import MIGRATIONS_DIR

    alembic_cfg = AlembicConfig()
    alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    alembic_cfg.set_main_option("sqlalchemy.url", url)

    if args.command == "upgrade":
        alembic_command.upgrade(alembic_cfg, args.revision)
    elif args.command == "downgrade":
        alembic_command.downgrade(alembic_cfg, args.revision)
    elif args.command == "current":
        alembic_command.current(alembic_cfg)
    elif args.command == "history":
        alembic_command.history(alembic_cfg)


if __name__ == "__main__":
    main()
