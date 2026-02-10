#!/usr/bin/env python3
"""
Wrapper Alembic pour ansibase-api

Gere les migrations API (ansibase_users, ansibase_api_keys, ansibase_audit_logs)
dans une table de suivi separee (alembic_version_api).

Verifie que le schema core est initialise avant d'appliquer les migrations API.

Usage (memes arguments que alembic) :
    python manage-db.py upgrade head
    python manage-db.py current
    python manage-db.py history
    python manage-db.py downgrade -1
"""

import sys
from pathlib import Path

from alembic.config import Config, CommandLine
from sqlalchemy import create_engine, text, inspect


def check_core_schema(database_url: str) -> None:
    """Verifie que les migrations core sont appliquees avant de lancer l'API."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            table_names = inspect(engine).get_table_names()

            if "alembic_version_core" not in table_names:
                print(
                    "ERREUR: le schema core n'est pas initialise.\n"
                    "Executez d'abord : ansibase-db --config ansibase.ini upgrade",
                    file=sys.stderr,
                )
                sys.exit(1)

            result = conn.execute(text("SELECT version_num FROM alembic_version_core"))
            versions = {row[0] for row in result}

            if not versions:
                print(
                    "ERREUR: aucune migration core appliquee.\n"
                    "Executez d'abord : ansibase-db --config ansibase.ini upgrade",
                    file=sys.stderr,
                )
                sys.exit(1)
    finally:
        engine.dispose()


def main():
    cli = CommandLine()

    if len(sys.argv) < 2:
        cli.parser.print_help()
        sys.exit(1)

    options = cli.parser.parse_args(sys.argv[1:])

    if not hasattr(options, "cmd") or options.cmd is None:
        cli.parser.print_help()
        sys.exit(1)

    try:
        cfg = Config(
            file_=options.config,
            ini_section=options.name,
            cmd_opts=options,
        )
    except Exception as e:
        print(f"ERREUR: configuration invalide: {e}", file=sys.stderr)
        cli.parser.print_help()
        sys.exit(1)

    # Ajouter le repertoire parent au sys.path pour importer app
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app.config import settings

    # Verifier le prerequis core avant upgrade/downgrade
    cmd_name = options.cmd[0].__name__ if options.cmd else ""
    if cmd_name in ("upgrade", "downgrade"):
        check_core_schema(settings.database_url)

    cli.run_cmd(cfg, options)


if __name__ == "__main__":
    main()
