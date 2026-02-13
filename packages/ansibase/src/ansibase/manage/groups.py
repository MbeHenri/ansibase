"""Sous-commandes CLI pour la gestion des groupes"""

from typing import Dict, List, Optional

import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from ansibase.models import (
    Group,
    Host,
    Variable,
    HostGroup,
    GroupVariable,
)
from ansibase.manage.utils import (
    db_session,
    load_yaml_file,
    resolve_group,
    resolve_variable,
    output_table,
    output_detail,
    output_list,
    confirm_action,
    is_json_mode,
)
from ansibase.manage.importers import ImportStats, import_group_recursive

PROTECTED_GROUPS = {"all", "ungrouped"}


@click.group()
def group():
    """Gestion des groupes."""
    pass


def _build_tree_lines(
    session: Session,
    parent_id: Optional[int],
    groups_by_parent: Dict[Optional[int], List[Group]],
    prefix: str = "",
    is_last: bool = True,
) -> List[str]:
    """Construit recursivement les lignes d'affichage de l'arborescence."""
    lines = []
    children = groups_by_parent.get(parent_id, [])
    for i, grp in enumerate(children):
        is_last_child = i == len(children) - 1
        if parent_id is None:
            # Racine : pas de prefixe
            connector = ""
            child_prefix = ""
        else:
            connector = prefix + ("└── " if is_last_child else "├── ")
            child_prefix = prefix + ("    " if is_last_child else "│   ")
        lines.append(f"{connector}{grp.name}")
        lines.extend(
            _build_tree_lines(
                session, grp.id, groups_by_parent, child_prefix, is_last_child
            )
        )
    return lines


@group.command("list")
@click.option("--tree", is_flag=True, default=False, help="Afficher en arborescence")
@click.pass_context
def group_list(ctx, tree):
    """Lister les groupes."""
    with db_session(ctx) as session:
        groups = session.execute(select(Group).order_by(Group.name)).scalars().all()

        if tree:
            if is_json_mode(ctx):
                # En mode JSON, on retourne une structure plate
                data = [
                    {"id": g.id, "name": g.name, "parent_id": g.parent_id}
                    for g in groups
                ]
                import json

                click.echo(json.dumps(data, indent=2, default=str))
                return

            # Construire un dict parent_id -> [enfants]
            groups_by_parent: Dict[Optional[int], List[Group]] = {}
            for g in groups:
                groups_by_parent.setdefault(g.parent_id, []).append(g)

            # Trouver les racines (parent_id = None)
            lines = _build_tree_lines(session, None, groups_by_parent)
            for line in lines:
                click.echo(line)
            return

        data = [
            {
                "id": g.id,
                "name": g.name,
                "parent_id": g.parent_id or "",
                "description": g.description or "",
            }
            for g in groups
        ]
        output_table(ctx, data, ["name", "parent_id", "description"])


def _collect_child_group_ids(session: Session, group_id: int) -> List[int]:
    """Collecte recursivement les IDs de tous les sous-groupes."""
    child_ids = []
    children = (
        session.execute(select(Group.id).where(Group.parent_id == group_id))
        .scalars()
        .all()
    )
    for cid in children:
        child_ids.append(cid)
        child_ids.extend(_collect_child_group_ids(session, cid))
    return child_ids


def _collect_parent_group_ids(session: Session, group_id: int) -> List[int]:
    """Collecte recursivement les IDs de tous les groupes parents."""
    parent_ids = []
    grp = session.get(Group, group_id)
    while grp and grp.parent_id:
        parent_ids.append(grp.parent_id)
        grp = session.get(Group, grp.parent_id)
    return parent_ids


@group.command("show")
@click.argument("ref")
@click.option(
    "--reveal", is_flag=True, default=False, help="Afficher les valeurs sensibles"
)
@click.option(
    "--inherited",
    is_flag=True,
    default=False,
    help="Inclure hotes des sous-groupes et variables heritees des parents",
)
@click.pass_context
def group_show(ctx, ref, reveal, inherited):
    """Afficher les details complets d'un groupe (info, hotes, variables)."""
    with db_session(ctx) as session:
        grp = resolve_group(session, ref)
        app = ctx.obj["app"]

        # Parent
        parent_name = None
        if grp.parent_id:
            parent = session.get(Group, grp.parent_id)
            parent_name = parent.name if parent else None

        # Enfants directs
        children = (
            session.execute(
                select(Group.name).where(Group.parent_id == grp.id).order_by(Group.name)
            )
            .scalars()
            .all()
        )

        # Info de base
        data = {
            "name": grp.name,
            "description": grp.description or "",
            "parent": parent_name or "(aucun)",
            "enfants": ", ".join(children) if children else "(aucun)",
            "cree_le": str(grp.created_at),
            "modifie_le": str(grp.updated_at),
        }
        output_detail(ctx, data)

        # Hotes
        group_ids_for_hosts = [grp.id]
        if inherited:
            group_ids_for_hosts.extend(_collect_child_group_ids(session, grp.id))

        hosts = (
            session.execute(
                select(Host.name)
                .join(HostGroup, HostGroup.host_id == Host.id)
                .where(HostGroup.group_id.in_(group_ids_for_hosts))
                .distinct()
                .order_by(Host.name)
            )
            .scalars()
            .all()
        )

        click.echo()
        title = "Hotes (herite) :" if inherited else "Hotes :"
        output_list(ctx, list(hosts), title=title)

        # Variables
        group_ids_for_vars = [grp.id]
        if inherited:
            group_ids_for_vars.extend(_collect_parent_group_ids(session, grp.id))

        gvs = session.execute(
            select(GroupVariable, Variable)
            .join(Variable, GroupVariable.var_id == Variable.id)
            .where(GroupVariable.group_id.in_(group_ids_for_vars))
            .order_by(Variable.var_key)
        ).all()

        # Deduplication : les variables du groupe courant ont priorite
        seen_keys = set()
        var_data = []
        for gv, var in gvs:
            if var.var_key in seen_keys:
                continue
            seen_keys.add(var.var_key)

            if var.is_sensitive:
                if reveal and gv.var_value_encrypted:
                    value = (
                        app.crypto.decrypt_value(session, gv.var_value_encrypted)
                        or "****"
                    )
                else:
                    value = "****"
            else:
                value = gv.var_value or ""

            row = {
                "var_key": var.var_key,
                "value": value,
                "sensitive": "oui" if var.is_sensitive else "non",
            }
            if inherited:
                if gv.group_id != grp.id:
                    src_grp = session.get(Group, gv.group_id)
                    row["source"] = src_grp.name if src_grp else ""
                else:
                    row["source"] = "(direct)"
            var_data.append(row)

        click.echo()
        columns = ["var_key", "value", "sensitive"]
        if inherited:
            columns.append("source")

        if not var_data:
            click.echo("Variables :")
            click.echo("  (aucune)")
        else:
            click.echo("Variables :")
            output_table(ctx, var_data, columns)


@group.command("create")
@click.argument("name")
@click.option("--description", default=None, help="Description du groupe")
@click.option("--parent", "parent_ref", default=None, help="Groupe parent (ID ou nom)")
@click.pass_context
def group_create(ctx, name, description, parent_ref):
    """Creer un nouveau groupe."""
    with db_session(ctx) as session:
        existing = session.query(Group).filter(Group.name == name).first()
        if existing:
            raise click.ClickException(f"Le groupe '{name}' existe deja.")

        parent_id = None
        if parent_ref:
            parent = resolve_group(session, parent_ref)
            parent_id = parent.id

        grp = Group(name=name, description=description, parent_id=parent_id)
        session.add(grp)
        session.flush()
        click.echo(f"Groupe '{grp.name}' cree (id={grp.id}).")


@group.command("update")
@click.argument("ref")
@click.option("--name", "new_name", default=None, help="Nouveau nom")
@click.option("--description", default=None, help="Nouvelle description")
@click.option("--parent", "parent_ref", default=None, help="Nouveau parent (ID ou nom)")
@click.pass_context
def group_update(ctx, ref, new_name, description, parent_ref):
    """Modifier un groupe."""
    with db_session(ctx) as session:
        grp = resolve_group(session, ref)
        changed = False

        if new_name is not None and new_name != grp.name:
            if grp.name in PROTECTED_GROUPS:
                raise click.ClickException(
                    f"Le groupe '{grp.name}' est protege et ne peut pas etre renomme."
                )
            existing = session.query(Group).filter(Group.name == new_name).first()
            if existing:
                raise click.ClickException(f"Le nom '{new_name}' est deja utilise.")
            grp.name = new_name
            changed = True

        if description is not None:
            grp.description = description
            changed = True

        if parent_ref is not None:
            parent = resolve_group(session, parent_ref)
            if parent.id == grp.id:
                raise click.ClickException(
                    "Un groupe ne peut pas etre son propre parent."
                )
            grp.parent_id = parent.id
            changed = True

        if not changed:
            click.echo("Aucune modification.")
            return

        session.flush()
        click.echo(f"Groupe '{grp.name}' mis a jour.")


@group.command("delete")
@click.argument("ref")
@click.option("--yes", is_flag=True, default=False, help="Confirmer sans demander")
@click.pass_context
def group_delete(ctx, ref, yes):
    """Supprimer un groupe."""
    with db_session(ctx) as session:
        grp = resolve_group(session, ref)

        if grp.name in PROTECTED_GROUPS:
            raise click.ClickException(
                f"Le groupe '{grp.name}' est protege et ne peut pas etre supprime."
            )

        if not yes and not confirm_action(f"Supprimer le groupe '{grp.name}' ?"):
            click.echo("Annule.")
            return

        session.delete(grp)
        session.flush()
        click.echo(f"Groupe '{grp.name}' supprime.")


@group.command("set-var")
@click.argument("ref")
@click.argument("key")
@click.argument("value")
@click.pass_context
def group_set_var(ctx, ref, key, value):
    """Assigner ou mettre a jour une variable sur un groupe (upsert)."""
    with db_session(ctx) as session:
        grp = resolve_group(session, ref)
        var = resolve_variable(session, key)
        app = ctx.obj["app"]

        gv = (
            session.query(GroupVariable)
            .filter(GroupVariable.group_id == grp.id, GroupVariable.var_id == var.id)
            .first()
        )

        if gv is None:
            gv = GroupVariable(group_id=grp.id, var_id=var.id)
            session.add(gv)

        if var.is_sensitive:
            gv.var_value_encrypted = app.crypto.encrypt_value(session, value)
            gv.var_value = None
        else:
            gv.var_value = value
            gv.var_value_encrypted = None

        session.flush()
        click.echo(f"Variable '{var.var_key}' definie sur le groupe '{grp.name}'.")


@group.command("unset-var")
@click.argument("ref")
@click.argument("key")
@click.pass_context
def group_unset_var(ctx, ref, key):
    """Retirer une variable d'un groupe."""
    with db_session(ctx) as session:
        grp = resolve_group(session, ref)
        var = resolve_variable(session, key)

        gv = (
            session.query(GroupVariable)
            .filter(GroupVariable.group_id == grp.id, GroupVariable.var_id == var.id)
            .first()
        )
        if not gv:
            raise click.ClickException(
                f"La variable '{var.var_key}' n'est pas definie sur le groupe '{grp.name}'."
            )

        session.delete(gv)
        session.flush()
        click.echo(f"Variable '{var.var_key}' retiree du groupe '{grp.name}'.")


@group.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--dry-run", is_flag=True, default=False, help="Simuler sans modifier la base"
)
@click.pass_context
def group_import(ctx, file, dry_run):
    """Importer des groupes depuis un fichier YAML au format inventaire Ansible.

    Le fichier doit suivre le format standard Ansible avec hosts, vars et children.
    """
    data = load_yaml_file(file)
    app = ctx.obj["app"]
    stats = ImportStats()

    if not isinstance(data, dict):
        raise click.ClickException("Le fichier YAML doit contenir un dictionnaire.")

    if dry_run:
        click.echo("[dry-run] Simulation, aucune modification ne sera appliquee.")

    with db_session(ctx, dry_run=dry_run) as session:
        for group_name, group_data in data.items():
            import_group_recursive(
                session, app.crypto, group_name, group_data, None, stats
            )

    prefix = "[dry-run] " if dry_run else ""
    click.echo(f"{prefix}Import termine : {stats.summary()}.")
