"""
Crée des données de démonstration pour l'application.
"""

import random
from datetime import datetime, timedelta

from faker import Faker
from werkzeug.security import generate_password_hash

from core.models.account import Account
from core.models.category import Category
from core.models.transactions import Transaction
from core.models.user import User

from .. import create_app, db


def create_demo_user():
    """Crée un utilisateur de démonstration."""
    user = User(
        username="demo_user",
        email="demo@example.com",
        password_hash=generate_password_hash("demo123"),
        first_name="Jean",
        last_name="Dupont",
        status="Actif",
        role_id=1,  # Admin
    )
    db.session.add(user)
    db.session.commit()
    return user


def create_demo_accounts(user_id):
    """Crée des comptes de démonstration."""
    accounts = [
        {
            "name": "Compte Courant",
            "type": "Courant",
            "balance": 2500.00,
            "iban": "FR7612345678901234567890123",
            "bic_swift": "ABCDEFGHIJK",
        },
        {
            "name": "Livret A",
            "type": "Épargne",
            "balance": 5000.00,
            "iban": "FR7698765432109876543210987",
            "bic_swift": "KJIHGFEDCBA",
        },
        {
            "name": "Compte Épargne",
            "type": "Épargne",
            "balance": 3500.00,
            "iban": "FR7611111222223333344444555",
            "bic_swift": "EFGHIJKLMNO",
        },
    ]

    created_accounts = []
    for acc in accounts:
        account = Account(
            nom_banque=acc["name"],
            type_compte=acc["type"],
            solde_actuel=acc["balance"],
            solde_disponible=acc["balance"],
            utilisateur_id=user_id,
            iban=acc["iban"],
            bic_swift=acc["bic_swift"],
        )
        db.session.add(account)
        created_accounts.append(account)

    db.session.commit()
    return created_accounts


def create_demo_categories(user_id):
    """Crée des catégories de démonstration."""
    categories = [
        {"name": "Alimentation", "type": "expense"},
        {"name": "Supermarché", "type": "expense"},
        {"name": "Restaurant", "type": "expense"},
        {"name": "Logement", "type": "expense"},
        {"name": "Loyer", "type": "expense"},
        {"name": "Charges", "type": "expense"},
        {"name": "Transports", "type": "expense"},
        {"name": "Essence", "type": "expense"},
        {"name": "Loisirs", "type": "expense"},
        {"name": "Santé", "type": "expense"},
        {"name": "Salaire", "type": "income"},
        {"name": "Autres revenus", "type": "income"},
    ]

    created_categories = []

    # Création des catégories
    for cat_data in categories:
        category = Category(
            nom_categorie=cat_data["name"],
            type_categorie=cat_data["type"],
            utilisateur_id=user_id,
        )
        db.session.add(category)
        created_categories.append(category)

    db.session.commit()
    return created_categories


def generate_transactions(user_id, accounts, categories, months=6):
    """Génère des transactions de démonstration."""
    fake = Faker("fr_FR")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30 * months)

    # Récupérer les catégories par nom pour un accès plus facile
    categories_by_name = {cat.nom_categorie: cat for cat in categories}
    accounts_by_name = {acc.nom_banque: acc for acc in accounts}

    # Transactions récurrentes (revenus et dépenses fixes)
    recurring_transactions = [
        # Revenus
        {
            "account": "Compte Courant",
            "category": "Salaire",
            "amount": 2500,
            "day": 28,
            "description": "Salaire",
            "type": "Depot",
        },
        # Dépenses fixes
        {
            "account": "Compte Courant",
            "category": "Loyer",
            "amount": -750,
            "day": 5,
            "description": "Loyer",
            "type": "Prelevement",
        },
        {
            "account": "Compte Courant",
            "category": "Charges",
            "amount": -120,
            "day": 10,
            "description": "Charges",
            "type": "Prelevement",
        },
        # Dépenses variables
        {
            "account": "Compte Courant",
            "category": "Supermarché",
            "amount": -300,
            "day": "random",
            "description": "Courses",
            "type": "PaiementCarte",
        },
        {
            "account": "Compte Courant",
            "category": "Essence",
            "amount": -60,
            "day": "random",
            "description": "Plein essence",
            "type": "PaiementCarte",
        },
    ]

    # Génération des transactions
    for rec in recurring_transactions:
        account = accounts_by_name.get(rec["account"])
        category = categories_by_name.get(rec["category"])

        if not account or not category:
            continue

        current_date = start_date
        while current_date <= end_date:
            # Pour les transactions mensuelles
            if isinstance(rec["day"], int):
                if current_date.day == min(
                    rec["day"], 28
                ):  # Gestion des mois avec moins de 31 jours
                    transaction_date = current_date.replace(day=min(rec["day"], 28))
                    create_transaction(
                        transaction_date, rec, account, category, user_id, fake
                    )
            # Pour les transactions aléatoires (2-3 par mois)
            elif (
                rec["day"] == "random" and random.random() < 0.1
            ):  # 10% de chance par jour
                transaction_date = current_date
                create_transaction(
                    transaction_date, rec, account, category, user_id, fake
                )

            current_date += timedelta(days=1)

    # Ajout de quelques transactions ponctuelles
    for _ in range(20):
        account = random.choice(accounts)
        category = random.choice(categories)

        # Déterminer le type de transaction en fonction du type de catégorie
        if category.type_categorie == "income":
            amount = random.uniform(100, 1000)
            transaction_type = random.choice(["Depot", "VirementExterne"])
        else:
            amount = -random.uniform(10, 200)
            transaction_type = random.choice(
                ["PaiementCarte", "PaiementCheque", "RetraitDistributeur"]
            )

        transaction = Transaction(
            montant=round(abs(amount), 2),
            libelle=fake.sentence(),
            date_heure_transaction=fake.date_time_between(
                start_date=start_date, end_date=end_date
            ),
            type_transaction=transaction_type,
            id_utilisateur=user_id,
            id_compte_source=account.id,
            id_compte_destination=(
                account.id
                if transaction_type in ["VirementExterne", "VirementInterne"]
                else None
            ),
            categorie_id=category.id,
            frais_transaction=0.0,
            devise="EUR",
            statut="Terminee",
            notes_internes="Transaction de démonstration",
        )
        db.session.add(transaction)

    db.session.commit()


def create_transaction(date, rec, account, category, user_id, fake=None):
    """Crée une transaction unique."""
    transaction_type = rec.get("type", "PaiementCarte")

    # Ajuster le montant pour certaines catégories
    amount = abs(rec["amount"])
    if fake and "Supermarché" in rec.get("libelle", ""):
        amount = round(amount * random.uniform(0.8, 1.2), 2)
    elif fake and "Essence" in rec.get("libelle", ""):
        amount = round(amount * random.uniform(0.9, 1.1), 2)

    # Créer le libellé
    libelle = rec.get(
        "libelle", fake.sentence() if fake else "Transaction sans libellé"
    )
    if fake and random.random() > 0.7:
        libelle += f" - {fake.sentence()}"

    transaction = Transaction(
        montant=amount,
        libelle=libelle,
        date_heure_transaction=date,
        type_transaction=transaction_type,
        id_utilisateur=user_id,
        id_compte_source=account.id,
        id_compte_destination=(
            account.id
            if transaction_type in ["VirementExterne", "VirementInterne"]
            else None
        ),
        categorie_id=category.id if category else None,
        frais_transaction=0.0,
        devise="EUR",
        statut="Terminee",
        notes_internes="Transaction de démonstration" if fake else None,
    )
    db.session.add(transaction)


def run():
    """Point d'entrée principal du script."""
    app = create_app()
    with app.app_context():
        print("🚀 Début de la création des données de démonstration...")

        # Nettoyer d'abord les anciennes données
        from .cleanup_demo_data import cleanup_demo_data

        cleanup_demo_data()

        print("👤 Création de l'utilisateur de démonstration...")
        user = create_demo_user()

        print("🏦 Création des comptes de démonstration...")
        accounts = create_demo_accounts(user.id)

        print("📂 Création des catégories de démonstration...")
        categories = create_demo_categories(user.id)

        print("💸 Génération des transactions de démonstration...")
        generate_transactions(user.id, accounts, categories, months=6)

        print("\n✅ Données de démonstration créées avec succès !")
        print("=" * 50)
        print("🔑 Identifiants de connexion :")
        print(f"   Email: demo@example.com")
        print(f"   Mot de passe: demo123")
        print("=" * 50)


if __name__ == "__main__":
    run()
