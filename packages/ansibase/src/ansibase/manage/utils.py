"""Utilitaires partages pour la CLI ansibase"""

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence

import click
import yaml
from sqlalchemy.orm import Session

from ansibase.models import Host, Group, Variable


@contextmanager
def db_session(
    ctx: click.Context, dry_run: bool = False
) -> Generator[Session, None, None]:
    """Context manager pour une session DB avec commit/rollback automatique.

    Si dry_run=True, la transaction est annulee (rollback) au lieu d'etre commitee.
    """
    app = ctx.obj["app"]
    session = app.db.get_session()
    try:
        yield session
        if dry_run:
            session.rollback()
        else:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def load_yaml_file(path: str) -> Any:
    """Charge et parse un fichier YAML. Leve une ClickException si le fichier est invalide."""
    filepath = Path(path)
    if not filepath.exists():
        raise click.ClickException(f"Fichier introuvable : {path}")
    if not filepath.is_file():
        raise click.ClickException(f"Ce n'est pas un fichier : {path}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise click.ClickException(f"Erreur de parsing YAML : {e}")
    if data is None:
        raise click.ClickException(f"Fichier YAML vide : {path}")
    return data


def resolve_host(session: Session, ref: str) -> Host:
    """Resout un hote par ID numerique ou nom."""
    if ref.isdigit():
        host = session.get(Host, int(ref))
    else:
        host = session.query(Host).filter(Host.name == ref).first()
    if not host:
        raise click.ClickException(f"Hote introuvable : {ref}")
    return host


def resolve_group(session: Session, ref: str) -> Group:
    """Resout un groupe par ID numerique ou nom."""
    if ref.isdigit():
        group = session.get(Group, int(ref))
    else:
        group = session.query(Group).filter(Group.name == ref).first()
    if not group:
        raise click.ClickException(f"Groupe introuvable : {ref}")
    return group


def resolve_variable(session: Session, ref: str) -> Variable:
    """Resout une variable par ID numerique ou var_key."""
    if ref.isdigit():
        var = session.get(Variable, int(ref))
    else:
        var = session.query(Variable).filter(Variable.var_key == ref).first()
    if not var:
        raise click.ClickException(f"Variable introuvable : {ref}")
    return var


def is_json_mode(ctx: click.Context) -> bool:
    """Verifie si la sortie JSON est activee."""
    return ctx.obj.get("json_output", False)


def output_table(
    ctx: click.Context,
    data: Sequence[Dict[str, Any]],
    columns: List[str],
) -> None:
    """Affiche des donnees en tableau ou JSON."""
    if is_json_mode(ctx):
        click.echo(json.dumps(list(data), indent=2, default=str))
        return

    if not data:
        click.echo("Aucun resultat.")
        return

    # Calcul des largeurs de colonnes
    widths = {col: len(col) for col in columns}
    for row in data:
        for col in columns:
            val = str(row.get(col, ""))
            widths[col] = max(widths[col], len(val))

    # En-tete
    header = "  ".join(col.upper().ljust(widths[col]) for col in columns)
    separator = "  ".join("-" * widths[col] for col in columns)
    click.echo(header)
    click.echo(separator)

    # Lignes
    for row in data:
        line = "  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
        click.echo(line)


def output_detail(ctx: click.Context, data: Dict[str, Any]) -> None:
    """Affiche un detail cle/valeur ou JSON."""
    if is_json_mode(ctx):
        click.echo(json.dumps(data, indent=2, default=str))
        return

    max_key_len = max(len(str(k)) for k in data.keys()) if data else 0
    for key, value in data.items():
        click.echo(f"  {str(key).ljust(max_key_len)} : {value}")


def output_list(
    ctx: click.Context, items: List[str], title: Optional[str] = None
) -> None:
    """Affiche une liste simple ou JSON."""
    if is_json_mode(ctx):
        click.echo(json.dumps(items, indent=2, default=str))
        return

    if title:
        click.echo(title)
    if not items:
        click.echo("  (vide)")
        return
    for item in items:
        click.echo(f"  - {item}")


def confirm_action(message: str) -> bool:
    """Demande une confirmation interactive."""
    return click.confirm(message, default=False)
