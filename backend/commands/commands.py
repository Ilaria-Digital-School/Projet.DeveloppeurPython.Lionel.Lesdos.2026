"""
Commandes en ligne de commande (CLI) pour l'administration de l'application.

Ce module contient des commandes utiles pour le développement et la maintenance.
"""

import os
from datetime import timezone

import click
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

from backend.core import models
from core.models.transactions import Transaction

from .extensions import db

# Importer les modèles de manière différée
User = models.User
Role = models.Role
Account = models.Account
Category = models.Category
# Transaction importé directement pour éviter conflit SQLAlchemy


# Importer les services de manière différée
def _import_services():
    from backend.core.services import create_account, create_category, create_user

    return create_user, create_account, create_category


create_user, create_account, create_category = _import_services()


def init_app(app):
    """Initialise les commandes CLI pour l'application."""
    app.cli.add_command(init_db)
    app.cli.add_command(create_admin)
    app.cli.add_command(create_test_data)
    app.cli.add_command(cleanup_data)


@click.command("init-db")
@with_appcontext
def init_db():
    """Initialise la base de données."""
    click.echo("Création de la base de données...")
    db.create_all()
    click.echo("Base de données créée avec succès!")


@click.command("create-admin")
@click.option("--username", prompt=True, help="Nom d'utilisateur administrateur")
@click.option("--email", prompt=True, help="Email administrateur")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Mot de passe administrateur",
)
@with_appcontext
def create_admin(username, email, password):
    """Crée un compte administrateur."""
    # Vérifier si un administrateur existe déjà
    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrateur du système")
        db.session.add(admin_role)
        db.session.commit()

    # Vérifier si l'utilisateur existe déjà
    user = User.query.filter_by(email=email).first()
    if user:
        if admin_role in user.roles:
            click.echo("Un administrateur avec cet email existe déjà!")
            return
        else:
            # Ajouter le rôle admin à l'utilisateur existant
            user.roles.append(admin_role)
            db.session.commit()
            click.echo(f"Rôle administrateur ajouté à l'utilisateur {email}")
            return

    # Créer un nouvel utilisateur admin
    # Note: le setter User.password hashe déjà le mot de passe,
    # ne pas passer generate_password_hash() (double hashage)
    user = User(
        username=username,
        email=email,
        password=password,
        is_active=True,
        email_verified=True,
    )
    user.roles.append(admin_role)

    db.session.add(user)
    db.session.commit()

    click.echo(f"Administrateur {username} créé avec succès!")


@click.command("create-test-data")
@click.option("--users", default=5, help="Nombre d'utilisateurs de test à créer")
@click.option("--accounts", default=3, help="Nombre de comptes par utilisateur")
@click.option("--categories", default=10, help="Nombre de catégories par utilisateur")
@click.option(
    "--transactions", default=100, help="Nombre total de transactions à créer"
)
@with_appcontext
def create_test_data(users, accounts, categories, transactions):
    """Crée des données de test pour le développement."""
    import random

    from faker import Faker

    fake = Faker("fr_FR")

    click.echo("Création des données de test...")

    # Créer des rôles s'ils n'existent pas
    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrateur du système")
        db.session.add(admin_role)

    user_role = Role.query.filter_by(name="user").first()
    if not user_role:
        user_role = Role(name="user", description="Utilisateur standard")
        db.session.add(user_role)

    db.session.commit()

    # Créer des utilisateurs de test
    test_users = []
    for i in range(users):
        username = f"testuser_{i+1}"
        email = f"test{i+1}@example.com"

        # Vérifier si l'utilisateur existe déjà
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                username=username,
                email=email,
                password=generate_password_hash("password123"),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                is_active=True,
                email_verified=True,
            )
            user.roles.append(user_role)
            db.session.add(user)
            test_users.append(user)
            click.echo(f"Création de l'utilisateur: {email}")

    db.session.commit()

    if not test_users:
        click.echo(
            "Aucun nouvel utilisateur créé. Les utilisateurs de test existent déjà."
        )
        test_users = User.query.all()

    # Créer des comptes pour chaque utilisateur
    all_accounts = []
    account_types = ["checking", "savings", "cash", "credit_card", "investment"]

    for user in test_users:
        for i in range(accounts):
            account = Account(
                user_id=user.id,
                name=f"Compte {i+1}",
                account_type=random.choice(account_types),
                currency="EUR",
                initial_balance=random.uniform(100, 10000),
                is_active=True,
            )
            db.session.add(account)
            all_accounts.append(account)
            click.echo(f"Création du compte: {account.name} pour {user.email}")

    db.session.commit()

    # Créer des catégories par défaut et personnalisées
    default_categories = [
        ("Alimentation", "expense"),
        ("Loisirs", "expense"),
        ("Logement", "expense"),
        ("Transport", "expense"),
        ("Santé", "expense"),
        ("Salaire", "income"),
        ("Cadeaux", "income"),
        ("Autres revenus", "income"),
    ]

    all_categories = []

    # Ajouter les catégories par défaut
    for name, cat_type in default_categories:
        category = Category(
            name=name, category_type=cat_type, is_default=True, is_active=True
        )
        db.session.add(category)
        all_categories.append(category)

    # Ajouter des catégories personnalisées pour chaque utilisateur
    for user in test_users:
        for i in range(categories):
            cat_type = random.choice(["expense", "income"])
            category = Category(
                user_id=user.id,
                name=f"Catégorie {i+1}",
                category_type=cat_type,
                is_active=True,
            )
            db.session.add(category)
            all_categories.append(category)
            click.echo(f"Création de la catégorie: {category.name} pour {user.email}")

    db.session.commit()

    # Créer des transactions
    transaction_types = ["expense", "income", "transfer"]

    for _ in range(transactions):
        user = random.choice(test_users)
        transaction_type = random.choice(transaction_types)
        amount = round(random.uniform(5, 1000), 2)
        date = fake.date_time_between(start_date="-1y", end_date="now")

        # Sélectionner des comptes et catégories aléatoires
        user_accounts = [acc for acc in all_accounts if acc.user_id == user.id]
        user_categories = [
            cat for cat in all_categories if cat.user_id == user.id or cat.is_default
        ]

        if not user_accounts or not user_categories:
            continue

        if transaction_type == "expense":
            account = random.choice(user_accounts)
            category = random.choice(
                [c for c in user_categories if c.category_type == "expense"]
            )

            transaction = Transaction(
                user_id=user.id,
                amount=amount,
                transaction_type="expense",
                source_account_id=account.id,
                category_id=category.id,
                label=fake.sentence(nb_words=4),
                transaction_date=date,
                notes=fake.sentence() if random.random() > 0.7 else None,
            )

        elif transaction_type == "income":
            account = random.choice(user_accounts)
            category = random.choice(
                [c for c in user_categories if c.category_type == "income"]
            )

            transaction = Transaction(
                user_id=user.id,
                amount=amount,
                transaction_type="income",
                destination_account_id=account.id,
                category_id=category.id,
                label=fake.sentence(nb_words=4),
                transaction_date=date,
                notes=fake.sentence() if random.random() > 0.7 else None,
            )

        else:  # transfer
            if len(user_accounts) < 2:
                continue

            source, destination = random.sample(user_accounts, 2)

            transaction = Transaction(
                user_id=user.id,
                amount=amount,
                transaction_type="transfer",
                source_account_id=source.id,
                destination_account_id=destination.id,
                transaction_fee=(
                    round(random.uniform(0, 5), 2) if random.random() > 0.8 else 0
                ),
                label=f"Virement vers {destination.name}",
                transaction_date=date,
                notes="Virement automatique" if random.random() > 0.7 else None,
            )

        db.session.add(transaction)

    db.session.commit()

    click.echo(f"Création de {transactions} transactions terminée!")
    click.echo("Données de test créées avec succès!")


@click.command("cleanup-data")
@click.option(
    "--days", default=30, help="Supprimer les données plus anciennes que X jours"
)
@with_appcontext
def cleanup_data(days):
    """Nettoie les anciennes données de l'application."""
    from datetime import datetime, timedelta

    threshold_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Supprimer les anciennes sessions
    sessions_dir = os.path.join(current_app.instance_path, "sessions")
    if os.path.exists(sessions_dir):
        for filename in os.listdir(sessions_dir):
            filepath = os.path.join(sessions_dir, filename)
            if os.path.isfile(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_mtime < threshold_date:
                    os.remove(filepath)

    # Supprimer les anciens fichiers temporaires
    temp_dir = os.path.join(current_app.instance_path, "temp")
    if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            if os.path.isfile(filepath):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if file_mtime < threshold_date:
                    os.remove(filepath)

    click.echo(f"Nettoyage des données terminé (données de plus de {days} jours).")
