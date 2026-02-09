"""Migrations Alembic pour le schema de base ansibase"""

from pathlib import Path

MIGRATIONS_DIR: Path = Path(__file__).resolve().parent
VERSIONS_DIR: Path = MIGRATIONS_DIR / "versions"
