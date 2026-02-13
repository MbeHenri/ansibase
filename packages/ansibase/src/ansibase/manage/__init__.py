"""CLI ansibase : gestion des hotes, groupes et variables"""

import os
from typing import Optional

import click

from ansibase.config import load_config
from ansibase.database import Database, DatabaseConfig
from ansibase.crypto import PgCrypto


class AppContext:
    """Contexte applicatif avec initialisation paresseuse de la config, DB et crypto."""

    def __init__(self, config_file: Optional[str] = None) -> None:
        self._config_file = config_file or os.environ.get(
            "ANSIBASE_CONFIG", "ansibase.ini"
        )
        self._config = None
        self._db = None
        self._crypto = None

    @property
    def config(self) -> dict:
        if self._config is None:
            self._config = load_config(self._config_file)
        return self._config

    @property
    def db(self) -> Database:
        if self._db is None:
            db_config = DatabaseConfig.from_dict(self.config["database"])
            self._db = Database(db_config)
        return self._db

    @property
    def crypto(self) -> PgCrypto:
        if self._crypto is None:
            self._crypto = PgCrypto(self.config["encryption"]["key"])
        return self._crypto

    def close(self) -> None:
        if self._db is not None:
            self._db.close()


@click.group()
@click.option(
    "-c", "--config",
    "config_file",
    default=None,
    envvar="ANSIBASE_CONFIG",
    help="Fichier de configuration INI ou YAML (defaut: ansibase.ini, env: ANSIBASE_CONFIG)",
)
@click.option(
    "--json", "json_output",
    is_flag=True,
    default=False,
    help="Sortie au format JSON",
)
@click.pass_context
def cli(ctx: click.Context, config_file: Optional[str], json_output: bool) -> None:
    """Ansibase — gestion des hotes, groupes et variables Ansible."""
    app = AppContext(config_file)
    ctx.ensure_object(dict)
    ctx.obj["app"] = app
    ctx.obj["json_output"] = json_output
    ctx.call_on_close(app.close)


# Import et enregistrement des sous-groupes
from ansibase.manage.hosts import host  # noqa: E402
from ansibase.manage.groups import group  # noqa: E402
from ansibase.manage.variables import var  # noqa: E402

cli.add_command(host)
cli.add_command(group)
cli.add_command(var)
