"""Sous-commandes CLI pour la gestion des hotes"""

from pathlib import Path

import click
from sqlalchemy import select

from ansibase.models import Host, Group, Variable, HostGroup, HostVariable
from ansibase.manage.utils import (
    db_session,
    load_yaml_file,
    resolve_host,
    resolve_group,
    resolve_variable,
    output_table,
    output_detail,
    output_list,
    confirm_action,
)
from ansibase.manage.importers import ImportStats, import_host_vars


@click.group()
def host():
    """Gestion des hotes."""
    pass


@host.command("list")
@click.option(
    "--active/--inactive", default=None, help="Filtrer par statut actif/inactif"
)
@click.option(
    "--group", "group_ref", default=None, help="Filtrer par groupe (ID ou nom)"
)
@click.option("--search", default=None, help="Rechercher par nom (contient)")
@click.pass_context
def host_list(ctx, active, group_ref, search):
    """Lister les hotes."""
    with db_session(ctx) as session:
        query = select(Host)

        if active is not None:
            query = query.where(Host.is_active == active)
        if search:
            query = query.where(Host.name.ilike(f"%{search}%"))
        if group_ref:
            grp = resolve_group(session, group_ref)
            query = query.join(HostGroup, HostGroup.host_id == Host.id).where(
                HostGroup.group_id == grp.id
            )

        query = query.order_by(Host.name)
        hosts = session.execute(query).scalars().all()

        data = [
            {
                "id": h.id,
                "name": h.name,
                "active": "oui" if h.is_active else "non",
                "description": h.description or "",
            }
            for h in hosts
        ]
        output_table(ctx, data, ["name", "active", "description"])


@host.command("show")
@click.argument("ref")
@click.option(
    "--reveal", is_flag=True, default=False, help="Afficher les valeurs sensibles"
)
@click.pass_context
def host_show(ctx, ref, reveal):
    """Afficher les details complets d'un hote (info, groupes, variables)."""
    with db_session(ctx) as session:
        h = resolve_host(session, ref)
        app = ctx.obj["app"]

        # Info de base
        data = {
            "name": h.name,
            "description": h.description or "",
            "active": "oui" if h.is_active else "non",
            "cree_le": str(h.created_at),
            "modifie_le": str(h.updated_at),
        }
        output_detail(ctx, data)

        # Groupes de l'hote
        groups = (
            session.execute(
                select(Group.name)
                .join(HostGroup, HostGroup.group_id == Group.id)
                .where(HostGroup.host_id == h.id)
                .order_by(Group.name)
            )
            .scalars()
            .all()
        )
        click.echo()
        output_list(ctx, list(groups), title="Groupes :")

        # Variables de l'hote
        hvs = session.execute(
            select(HostVariable, Variable)
            .join(Variable, HostVariable.var_id == Variable.id)
            .where(HostVariable.host_id == h.id)
            .order_by(Variable.var_key)
        ).all()

        click.echo()
        if not hvs:
            click.echo("Variables :")
            click.echo("  (aucune)")
        else:
            var_data = []
            for hv, var in hvs:
                if var.is_sensitive:
                    if reveal and hv.var_value_encrypted:
                        value = (
                            app.crypto.decrypt_value(session, hv.var_value_encrypted)
                            or "****"
                        )
                    else:
                        value = "****"
                else:
                    value = hv.var_value or ""

                var_data.append(
                    {
                        "var_key": var.var_key,
                        "value": value,
                        "sensitive": "oui" if var.is_sensitive else "non",
                    }
                )

            click.echo("Variables :")
            output_table(ctx, var_data, ["var_key", "value", "sensitive"])


@host.command("create")
@click.argument("name")
@click.option("--description", default=None, help="Description de l'hote")
@click.option("--inactive", is_flag=True, default=False, help="Creer l'hote inactif")
@click.pass_context
def host_create(ctx, name, description, inactive):
    """Creer un nouvel hote."""
    with db_session(ctx) as session:
        existing = session.query(Host).filter(Host.name == name).first()
        if existing:
            raise click.ClickException(f"L'hote '{name}' existe deja.")

        h = Host(name=name, description=description, is_active=not inactive)
        session.add(h)
        session.flush()
        click.echo(f"Hote '{h.name}' cree (id={h.id}).")


@host.command("update")
@click.argument("ref")
@click.option("--name", "new_name", default=None, help="Nouveau nom")
@click.option("--description", default=None, help="Nouvelle description")
@click.option("--active/--inactive", default=None, help="Activer/desactiver l'hote")
@click.pass_context
def host_update(ctx, ref, new_name, description, active):
    """Modifier un hote."""
    with db_session(ctx) as session:
        h = resolve_host(session, ref)
        changed = False

        if new_name is not None and new_name != h.name:
            existing = session.query(Host).filter(Host.name == new_name).first()
            if existing:
                raise click.ClickException(f"Le nom '{new_name}' est deja utilise.")
            h.name = new_name
            changed = True
        if description is not None:
            h.description = description
            changed = True
        if active is not None:
            h.is_active = active
            changed = True

        if not changed:
            click.echo("Aucune modification.")
            return

        session.flush()
        click.echo(f"Hote '{h.name}' mis a jour.")


@host.command("delete")
@click.argument("ref")
@click.option("--yes", is_flag=True, default=False, help="Confirmer sans demander")
@click.pass_context
def host_delete(ctx, ref, yes):
    """Supprimer un hote."""
    with db_session(ctx) as session:
        h = resolve_host(session, ref)
        if not yes and not confirm_action(f"Supprimer l'hote '{h.name}' ?"):
            click.echo("Annule.")
            return

        session.delete(h)
        session.flush()
        click.echo(f"Hote '{h.name}' supprime.")


@host.command("add-group")
@click.argument("ref")
@click.argument("group_ref")
@click.pass_context
def host_add_group(ctx, ref, group_ref):
    """Ajouter un hote a un groupe."""
    with db_session(ctx) as session:
        h = resolve_host(session, ref)
        grp = resolve_group(session, group_ref)

        existing = (
            session.query(HostGroup)
            .filter(HostGroup.host_id == h.id, HostGroup.group_id == grp.id)
            .first()
        )
        if existing:
            raise click.ClickException(
                f"L'hote '{h.name}' est deja dans le groupe '{grp.name}'."
            )

        hg = HostGroup(host_id=h.id, group_id=grp.id)
        session.add(hg)
        session.flush()
        click.echo(f"Hote '{h.name}' ajoute au groupe '{grp.name}'.")


@host.command("remove-group")
@click.argument("ref")
@click.argument("group_ref")
@click.pass_context
def host_remove_group(ctx, ref, group_ref):
    """Retirer un hote d'un groupe."""
    with db_session(ctx) as session:
        h = resolve_host(session, ref)
        grp = resolve_group(session, group_ref)

        hg = (
            session.query(HostGroup)
            .filter(HostGroup.host_id == h.id, HostGroup.group_id == grp.id)
            .first()
        )
        if not hg:
            raise click.ClickException(
                f"L'hote '{h.name}' n'est pas dans le groupe '{grp.name}'."
            )

        session.delete(hg)
        session.flush()
        click.echo(f"Hote '{h.name}' retire du groupe '{grp.name}'.")


@host.command("set-var")
@click.argument("ref")
@click.argument("key")
@click.argument("value")
@click.pass_context
def host_set_var(ctx, ref, key, value):
    """Assigner ou mettre a jour une variable sur un hote (upsert)."""
    with db_session(ctx) as session:
        h = resolve_host(session, ref)
        var = resolve_variable(session, key)
        app = ctx.obj["app"]

        hv = (
            session.query(HostVariable)
            .filter(HostVariable.host_id == h.id, HostVariable.var_id == var.id)
            .first()
        )

        if hv is None:
            hv = HostVariable(host_id=h.id, var_id=var.id)
            session.add(hv)

        if var.is_sensitive:
            hv.var_value_encrypted = app.crypto.encrypt_value(session, value)
            hv.var_value = None
        else:
            hv.var_value = value
            hv.var_value_encrypted = None

        session.flush()
        click.echo(f"Variable '{var.var_key}' definie sur l'hote '{h.name}'.")


@host.command("unset-var")
@click.argument("ref")
@click.argument("key")
@click.pass_context
def host_unset_var(ctx, ref, key):
    """Retirer une variable d'un hote."""
    with db_session(ctx) as session:
        h = resolve_host(session, ref)
        var = resolve_variable(session, key)

        hv = (
            session.query(HostVariable)
            .filter(HostVariable.host_id == h.id, HostVariable.var_id == var.id)
            .first()
        )
        if not hv:
            raise click.ClickException(
                f"La variable '{var.var_key}' n'est pas definie sur l'hote '{h.name}'."
            )

        session.delete(hv)
        session.flush()
        click.echo(f"Variable '{var.var_key}' retiree de l'hote '{h.name}'.")


@host.command("import")
@click.argument("file", type=click.Path(exists=True))
@click.option("--name", "hostname", default=None, help="Nom de l'hote (format plat)")
@click.option(
    "--dry-run", is_flag=True, default=False, help="Simuler sans modifier la base"
)
@click.pass_context
def host_import(ctx, file, hostname, dry_run):
    """Importer des hotes et variables depuis un fichier YAML.

    Format A (plat, un seul hote) : toutes les valeurs sont des scalaires.
    Necessite --name pour definir le hostname.

    Format B (multi-hotes) : chaque cle de premier niveau est un hostname
    avec un dict de variables.
    """
    data = load_yaml_file(file)
    app = ctx.obj["app"]
    stats = ImportStats()

    if not isinstance(data, dict):
        raise click.ClickException("Le fichier YAML doit contenir un dictionnaire.")

    # Detection du format : si toutes les valeurs sont des scalaires → format A
    is_flat = all(not isinstance(v, dict) for v in data.values())

    if dry_run:
        click.echo("[dry-run] Simulation, aucune modification ne sera appliquee.")

    with db_session(ctx, dry_run=dry_run) as session:
        if is_flat:
            # Format A : hote unique
            if not hostname:
                # Deduire du nom de fichier
                hostname = Path(file).stem
            import_host_vars(session, app.crypto, hostname, data, stats)
        else:
            # Format B : multi-hotes
            for host_name, host_vars in data.items():
                if not isinstance(host_vars, dict):
                    raise click.ClickException(
                        f"Les variables de '{host_name}' doivent etre un dictionnaire."
                    )
                import_host_vars(session, app.crypto, host_name, host_vars, stats)

    prefix = "[dry-run] " if dry_run else ""
    click.echo(f"{prefix}Import termine : {stats.summary()}.")
