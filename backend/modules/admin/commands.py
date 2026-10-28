# backend/admin/commands.py
import logging

import click
from werkzeug.security import generate_password_hash

from core.extensions import db
from core.models.role import Role
from core.models.user import User

logger = logging.getLogger(__name__)


def get_or_create_role(name, description=""):
    """Récupère ou crée un rôle avec les permissions par défaut."""
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name, description=description)
        db.session.add(role)
        db.session.commit()
    return role


@click.group()
def admin():
    """Commandes d'administration."""


@admin.command("create-admin")
@click.option("--email", prompt="Email", default="admin@example.com")
@click.option("--username", prompt="Nom d'utilisateur", default="admin")
@click.password_option(confirmation_prompt=True)
@click.option("--update", is_flag=True, help="Mettre à jour l'administrateur existant")
def create_admin(email, username, password, update):
    """Crée ou met à jour un utilisateur administrateur."""
    try:
        # Vérifier si l'utilisateur existe déjà
        admin = User.query.filter_by(email=email).first()

        if admin and not update:
            click.echo(
                "❌ L'utilisateur admin existe déjà. Utilisez --update pour le mettre à jour."
            )
            click.echo(f"Email: {admin.email}")
            click.echo(f"Nom d'utilisateur: {admin.username}")
            click.echo(f"Admin: {'Oui' if admin.is_admin else 'Non'}")
            return

        if not admin:
            # Créer un nouvel administrateur
            admin = User(
                username=username,
                email=email,
                first_name="Admin",
                last_name="System",
                email_verified=True,
            )
            click.echo("✅ Création d'un nouvel administrateur...")
        else:
            click.echo("🔄 Mise à jour de l'administrateur existant...")

        # Mettre à jour les informations
        admin.username = username
        admin.password_hash = generate_password_hash(password)

        # S'assurer que le rôle admin existe
        admin_role = get_or_create_role("admin", "Administrateur avec tous les droits")
        if admin_role not in admin.roles:
            admin.roles.append(admin_role)

        db.session.add(admin)
        db.session.commit()

        click.echo(
            f"✅ Administrateur {'créé' if not update else 'mis à jour'} avec succès !"
        )
        click.echo(f"  • Email: {admin.email}")
        click.echo(f"  • Nom d'utilisateur: {admin.username}")
        click.echo(f"  • Rôles: {', '.join([r.name for r in admin.roles])}")

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Erreur lors de la création/mise à jour de l'administrateur: {str(e)}"
        )
        click.echo(f"❌ Erreur: {str(e)}", err=True)
        raise click.Abort()


def init_commands(app):
    """Enregistre les commandes CLI personnalisées."""
    try:
        app.cli.add_command(admin)
        logger.info("Commandes d'administration enregistrées avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement des commandes: {str(e)}")
        raise
