#!/usr/bin/env python3
"""
Wrapper Alembic pour ansibase-api

Combine les migrations core (package ansibase) et API avant de deleguer
a la CLI Alembic. Necessite le package ansibase installe.

Usage (memes arguments que alembic) :
    python manage_db.py upgrade heads
    python manage_db.py current
    python manage_db.py history
    python manage_db.py downgrade -1
"""

import sys
from pathlib import Path

from alembic.config import Config, CommandLine


def main():
    cli = CommandLine()

    # On affiche l'aide si on a aucun argument
    if len(sys.argv) < 2:
        cli.parser.print_help()
        sys.exit(1)

    options = cli.parser.parse_args(sys.argv[1:])

    # On affiche l'aide si pas de sous-commande
    if not hasattr(options, "cmd") or options.cmd is None:
        cli.parser.print_help()
        sys.exit(1)

    # On construit la configuration depuis alembic.ini
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

    # on recupere le repertoire des migrations de l'api
    api_versions_dir = str(Path(__file__).resolve().parent / "alembic" / "versions")
    try:
        from ansibase.migrations import VERSIONS_DIR as core_versions_dir

        # on separe les deux repertoire avec un point-virgule pour que Alembic les traite comme des emplacements distincts
        version_locations = f"{core_versions_dir};{api_versions_dir}"
    except ImportError:
        # si le package ansibase n'est pas installé, on se contente du repertoire de l'api
        version_locations = api_versions_dir
    cfg.set_main_option("version_locations", version_locations)

    # Multi-branches (core + api) : "head" -> "heads" pour couvrir toutes les branches
    # on change la valeur de options.revision avant de deleguer a la CLI Alembic, qui va ensuite la passer a env.py
    if hasattr(options, "revision") and options.revision == "head":
        options.revision = "heads"

    cli.run_cmd(cfg, options)


if __name__ == "__main__":
    main()
