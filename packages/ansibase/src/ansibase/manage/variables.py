"""Sous-commandes CLI pour la gestion des variables"""

import click
from sqlalchemy import select

from ansibase.models import Variable
from ansibase.manage.utils import (
    db_session,
    resolve_variable,
    output_table,
    confirm_action,
)


@click.group()
def var():
    """Gestion des variables."""
    pass


@var.command("list")
@click.option(
    "--sensitive",
    is_flag=True,
    default=False,
    help="Uniquement les variables sensibles",
)
@click.option(
    "--builtin",
    is_flag=True,
    default=False,
    help="Uniquement les variables Ansible builtin",
)
@click.option(
    "--type", "var_type", default=None, help="Filtrer par type (string, integer, etc.)"
)
@click.pass_context
def var_list(ctx, sensitive, builtin, var_type):
    """Lister le catalogue de variables."""
    with db_session(ctx) as session:
        query = select(Variable).order_by(Variable.var_key)

        if sensitive:
            query = query.where(Variable.is_sensitive == True)  # noqa: E712
        if builtin:
            query = query.where(Variable.is_ansible_builtin == True)  # noqa: E712
        if var_type:
            query = query.where(Variable.var_type == var_type)

        variables = session.execute(query).scalars().all()

        data = [
            {
                "id": v.id,
                "var_key": v.var_key,
                "type": v.var_type,
                "sensitive": "oui" if v.is_sensitive else "non",
                "builtin": "oui" if v.is_ansible_builtin else "non",
                "description": v.description or "",
            }
            for v in variables
        ]
        output_table(
            ctx, data, ["var_key", "type", "sensitive", "builtin", "description"]
        )


@var.command("create")
@click.argument("var_key")
@click.option("--description", default=None, help="Description de la variable")
@click.option(
    "--sensitive", is_flag=True, default=False, help="Variable sensible (chiffree)"
)
@click.option(
    "--type", "var_type", default="string", help="Type de variable (defaut: string)"
)
@click.option("--default", "default_value", default=None, help="Valeur par defaut")
@click.option("--regex", default=None, help="Regex de validation")
@click.pass_context
def var_create(ctx, var_key, description, sensitive, var_type, default_value, regex):
    """Creer une variable dans le catalogue."""
    with db_session(ctx) as session:
        existing = session.query(Variable).filter(Variable.var_key == var_key).first()
        if existing:
            raise click.ClickException(f"La variable '{var_key}' existe deja.")

        v = Variable(
            var_key=var_key,
            description=description,
            is_sensitive=sensitive,
            var_type=var_type,
            default_value=default_value,
            validation_regex=regex,
        )
        session.add(v)
        session.flush()
        click.echo(f"Variable '{v.var_key}' creee (id={v.id}).")


@var.command("update")
@click.argument("ref")
@click.option("--description", default=None, help="Nouvelle description")
@click.option("--sensitive/--no-sensitive", default=None, help="Sensible ou non")
@click.option("--type", "var_type", default=None, help="Nouveau type")
@click.option(
    "--default", "default_value", default=None, help="Nouvelle valeur par defaut"
)
@click.option("--regex", default=None, help="Nouvelle regex de validation")
@click.pass_context
def var_update(ctx, ref, description, sensitive, var_type, default_value, regex):
    """Modifier les metadonnees d'une variable."""
    with db_session(ctx) as session:
        v = resolve_variable(session, ref)
        changed = False

        if description is not None:
            v.description = description
            changed = True
        if sensitive is not None:
            v.is_sensitive = sensitive
            changed = True
        if var_type is not None:
            v.var_type = var_type
            changed = True
        if default_value is not None:
            v.default_value = default_value
            changed = True
        if regex is not None:
            v.validation_regex = regex
            changed = True

        if not changed:
            click.echo("Aucune modification.")
            return

        session.flush()
        click.echo(f"Variable '{v.var_key}' mise a jour.")


@var.command("delete")
@click.argument("ref")
@click.option(
    "--force", is_flag=True, default=False, help="Forcer la suppression des builtins"
)
@click.option("--yes", is_flag=True, default=False, help="Confirmer sans demander")
@click.pass_context
def var_delete(ctx, ref, force, yes):
    """Supprimer une variable du catalogue."""
    with db_session(ctx) as session:
        v = resolve_variable(session, ref)

        if v.is_ansible_builtin and not force:
            raise click.ClickException(
                f"La variable '{v.var_key}' est une builtin Ansible. "
                "Utilisez --force pour la supprimer."
            )

        if not yes and not confirm_action(f"Supprimer la variable '{v.var_key}' ?"):
            click.echo("Annule.")
            return

        session.delete(v)
        session.flush()
        click.echo(f"Variable '{v.var_key}' supprimee.")
