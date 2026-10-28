#!/usr/bin/env python3
"""
Script pour creer un utilisateur demo complet avec des donnees realistes
pour faire des demonstrations de l'application.

Usage:
    export DEMO_PASSWORD='...'   # mot de passe du compte demo (obligatoire)
    export DATABASE_URL='postgresql://...'
    cd /var/www/Appli_Web_Budget/backend && ../venv/bin/python3 scripts/create_demo_user.py

Connexion:
    Email: demo@budget.fr
"""

import os
import random
import sys
from datetime import datetime, timedelta

import psycopg2
from werkzeug.security import generate_password_hash

DEMO_EMAIL = "demo@budget.fr"
DEMO_USERNAME = "demo"
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DEMO_PASSWORD:
    sys.exit("ERREUR : la variable d'environnement DEMO_PASSWORD est obligatoire.")
if not DATABASE_URL:
    sys.exit("ERREUR : la variable d'environnement DATABASE_URL est obligatoire.")


def create_demo_user():
    """Cree un utilisateur demo avec comptes, categories, transactions et budgets."""

    print("=== Creation du compte demo ===\n")

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        # ------------------------------------------------------------------
        # 0. Nettoyage : supprimer l'utilisateur demo existant
        # ------------------------------------------------------------------
        cursor.execute("SELECT id FROM users WHERE email = %s", (DEMO_EMAIL,))
        existing = cursor.fetchone()

        if existing:
            old_id = existing[0]
            print(f"Utilisateur demo existant (ID: {old_id}), suppression...")
            cursor.execute("DELETE FROM transactions WHERE user_id = %s", (old_id,))
            cursor.execute("DELETE FROM budgets WHERE user_id = %s", (old_id,))
            cursor.execute("DELETE FROM categories WHERE user_id = %s", (old_id,))
            cursor.execute(
                'DELETE FROM "ComptesBancaires" WHERE utilisateur_id = %s', (old_id,)
            )
            cursor.execute("DELETE FROM user_roles WHERE user_id = %s", (old_id,))
            cursor.execute("DELETE FROM users WHERE id = %s", (old_id,))
            print("   Donnees precedentes supprimees.\n")

        # ------------------------------------------------------------------
        # 1. Utilisateur
        # ------------------------------------------------------------------
        now = datetime.now(tz=None)
        now_iso = now.isoformat()
        password_hash = generate_password_hash(DEMO_PASSWORD, method="pbkdf2:sha256")

        cursor.execute(
            """
            INSERT INTO users (
                username, email, password_hash,
                first_name, last_name,
                is_active, email_verified,
                two_factor_enabled, login_count,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                DEMO_USERNAME,
                DEMO_EMAIL,
                password_hash,
                "Demo",
                "Utilisateur",
                True,
                True,
                False,
                0,
                now_iso,
                now_iso,
            ),
        )
        user_id = cursor.fetchone()[0]
        print(f"Utilisateur cree (ID: {user_id})")

        # Assigner le role 'user'
        cursor.execute("SELECT id FROM roles WHERE name = 'user'")
        role_row = cursor.fetchone()
        if role_row:
            cursor.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                (user_id, role_row[0]),
            )
            print(f"   Role 'user' assigne (role ID: {role_row[0]})")
        else:
            print("   ATTENTION : role 'user' introuvable, aucun role assigne.")

        # ------------------------------------------------------------------
        # 2. Comptes bancaires
        # ------------------------------------------------------------------
        print("\nCreation des comptes bancaires...")

        accounts_data = [
            # (nom_banque, type_compte, nom_banque_detail, est_compte_principal)
            ("Compte courant BNP", "courant", "BNP Paribas", True),
            ("Livret A Caisse d'Epargne", "epargne", "Caisse d'Epargne", False),
            ("Compte joint SG", "courant", "Societe Generale", False),
        ]

        account_ids = []
        for nom, type_compte, banque, principal in accounts_data:
            cursor.execute(
                """
                INSERT INTO "ComptesBancaires" (
                    utilisateur_id, nom_banque, type_compte,
                    solde_actuel, devise, nom_banque_detail,
                    est_actif, est_compte_principal,
                    date_ouverture, date_mise_a_jour
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_compte
            """,
                (
                    user_id,
                    nom,
                    type_compte,
                    0.0,
                    "EUR",
                    banque,
                    True,
                    principal,
                    now_iso,
                    now_iso,
                ),
            )
            account_ids.append(cursor.fetchone()[0])
            print(f"   Compte '{nom}' cree (ID: {account_ids[-1]})")

        acct_bnp, acct_livret, acct_joint = account_ids

        # ------------------------------------------------------------------
        # 3. Categories
        # ------------------------------------------------------------------
        print("\nCreation des categories...")

        categories_def = [
            # (name, description, is_expense, category_type, color, icon)
            (
                "Alimentation",
                "Courses et nourriture",
                True,
                "expense",
                "#FF6B6B",
                "fa-utensils",
            ),
            (
                "Transport",
                "Essence, transports en commun",
                True,
                "expense",
                "#4ECDC4",
                "fa-car",
            ),
            (
                "Logement",
                "Loyer, charges, electricite",
                True,
                "expense",
                "#45B7D1",
                "fa-home",
            ),
            (
                "Loisirs",
                "Sorties, cinema, hobbies",
                True,
                "expense",
                "#96CEB4",
                "fa-gamepad",
            ),
            ("Sante", "Medecin, pharmacie", True, "expense", "#FFEAA7", "fa-heartbeat"),
            (
                "Vetements",
                "Habits, chaussures",
                True,
                "expense",
                "#DDA0DD",
                "fa-tshirt",
            ),
            (
                "Abonnements",
                "Netflix, Spotify, telephone",
                True,
                "expense",
                "#74B9FF",
                "fa-redo",
            ),
            (
                "Restaurants",
                "Restaurants et sorties",
                True,
                "expense",
                "#E17055",
                "fa-utensils",
            ),
            (
                "Salaire",
                "Revenus du travail",
                False,
                "income",
                "#00B894",
                "fa-briefcase",
            ),
            (
                "Freelance",
                "Revenus independants",
                False,
                "income",
                "#6C5CE7",
                "fa-laptop-code",
            ),
            (
                "Remboursements",
                "Remboursements divers",
                False,
                "income",
                "#55EFC4",
                "fa-undo",
            ),
            (
                "Autres revenus",
                "Revenus divers",
                False,
                "income",
                "#A29BFE",
                "fa-coins",
            ),
        ]

        cat_ids = {}  # name -> id
        for name, desc, is_expense, cat_type, color, icon in categories_def:
            cursor.execute(
                """
                INSERT INTO categories (
                    user_id, name, description,
                    is_expense, category_type, color, icon,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    user_id,
                    name,
                    desc,
                    is_expense,
                    cat_type,
                    color,
                    icon,
                    now_iso,
                    now_iso,
                ),
            )
            cat_ids[name] = cursor.fetchone()[0]
            print(f"   Categorie '{name}' creee (ID: {cat_ids[name]})")

        # ------------------------------------------------------------------
        # 4. Transactions (~60 sur 90 jours)
        # ------------------------------------------------------------------
        print("\nCreation des transactions...")

        today = now.date()
        random.seed(42)  # resultats reproductibles

        def date_at(days_ago, hour=10):
            """Retourne un datetime ISO pour N jours dans le passe."""
            d = today - timedelta(days=days_ago)
            return datetime(
                d.year, d.month, d.day, hour, random.randint(0, 59)
            ).isoformat()

        # Repartition des transactions sur 3 mois
        transactions = []

        # --- Salaires (2 800 EUR, le 1er de chaque mois) ---
        for m in range(3):
            d = today.replace(day=1) - timedelta(days=30 * m)
            d = d.replace(day=1)
            transactions.append(
                (
                    acct_bnp,
                    cat_ids["Salaire"],
                    2800.00,
                    "salaire",
                    "Virement salaire",
                    "Salaire mensuel",
                    datetime(d.year, d.month, d.day, 8, 0).isoformat(),
                )
            )

        # --- Loyer (-950 EUR, le 5 de chaque mois) ---
        for m in range(3):
            d = today.replace(day=5) - timedelta(days=30 * m)
            d = d.replace(day=5)
            transactions.append(
                (
                    acct_bnp,
                    cat_ids["Logement"],
                    -950.00,
                    "loyer",
                    "Loyer appartement",
                    "Prelevement loyer mensuel",
                    datetime(d.year, d.month, d.day, 9, 0).isoformat(),
                )
            )

        # --- Abonnements mensuels ---
        abonnements = [
            ("Netflix", -13.49),
            ("Spotify", -9.99),
            ("Forfait mobile", -19.99),
            ("Salle de sport", -29.90),
        ]
        for m in range(3):
            for libelle, montant in abonnements:
                d_offset = random.randint(1, 10) + 30 * m
                transactions.append(
                    (
                        acct_bnp,
                        cat_ids["Abonnements"],
                        montant,
                        "abonnement",
                        libelle,
                        f"{libelle} - prelevement mensuel",
                        date_at(d_offset),
                    )
                )

        # --- Courses alimentaires ---
        courses = [
            ("Courses Carrefour", -87.45),
            ("Courses Leclerc", -65.30),
            ("Courses Lidl", -42.80),
            ("Marche bio", -38.50),
            ("Boulangerie", -8.20),
            ("Primeur", -15.60),
            ("Courses Monoprix", -53.90),
            ("Courses Auchan", -72.15),
            ("Epicerie", -22.40),
            ("Boulangerie", -6.50),
            ("Courses Carrefour", -95.20),
            ("Courses Lidl", -48.70),
        ]
        for i, (libelle, montant) in enumerate(courses):
            d_offset = int(i * 90 / len(courses)) + random.randint(0, 3)
            transactions.append(
                (
                    acct_bnp,
                    cat_ids["Alimentation"],
                    montant,
                    "achat",
                    libelle,
                    "Courses alimentaires",
                    date_at(d_offset),
                )
            )

        # --- Restaurants ---
        restos = [
            ("Restaurant Le Bistrot", -32.50),
            ("Sushi Shop", -28.00),
            ("Pizza Hut", -22.90),
            ("Brasserie du coin", -45.00),
            ("Dejeuner collegues", -18.50),
            ("Restaurant italien", -38.00),
        ]
        for i, (libelle, montant) in enumerate(restos):
            d_offset = random.randint(5, 85)
            transactions.append(
                (
                    acct_bnp,
                    cat_ids["Restaurants"],
                    montant,
                    "achat",
                    libelle,
                    "Repas au restaurant",
                    date_at(d_offset, 12),
                )
            )

        # --- Transport ---
        transports = [
            ("Essence Total", -65.00),
            ("Parking centre-ville", -12.00),
            ("Peage autoroute", -18.50),
            ("Essence BP", -58.30),
            ("Pass Navigo", -84.10),
            ("Essence Total", -61.40),
        ]
        for i, (libelle, montant) in enumerate(transports):
            d_offset = random.randint(2, 85)
            transactions.append(
                (
                    acct_bnp,
                    cat_ids["Transport"],
                    montant,
                    "achat",
                    libelle,
                    "Deplacement",
                    date_at(d_offset),
                )
            )

        # --- Loisirs ---
        loisirs = [
            ("Cinema Pathe", -24.00),
            ("Livre Amazon", -18.90),
            ("Concert", -55.00),
            ("Jeu video Steam", -39.99),
        ]
        for i, (libelle, montant) in enumerate(loisirs):
            d_offset = random.randint(5, 80)
            transactions.append(
                (
                    acct_joint,
                    cat_ids["Loisirs"],
                    montant,
                    "achat",
                    libelle,
                    "Loisirs et divertissement",
                    date_at(d_offset),
                )
            )

        # --- Sante ---
        transactions.append(
            (
                acct_bnp,
                cat_ids["Sante"],
                -25.00,
                "achat",
                "Pharmacie",
                "Medicaments",
                date_at(20),
            )
        )
        transactions.append(
            (
                acct_bnp,
                cat_ids["Sante"],
                -50.00,
                "achat",
                "Consultation medecin",
                "Visite generaliste",
                date_at(45),
            )
        )

        # --- Vetements ---
        transactions.append(
            (
                acct_joint,
                cat_ids["Vetements"],
                -89.90,
                "achat",
                "Zara",
                "Vetements hiver",
                date_at(35),
            )
        )
        transactions.append(
            (
                acct_joint,
                cat_ids["Vetements"],
                -45.00,
                "achat",
                "Decathlon",
                "Chaussures sport",
                date_at(60),
            )
        )

        # --- Revenus freelance ---
        transactions.append(
            (
                acct_bnp,
                cat_ids["Freelance"],
                750.00,
                "revenu_autre",
                "Mission dev web",
                "Facture client X",
                date_at(25),
            )
        )
        transactions.append(
            (
                acct_bnp,
                cat_ids["Freelance"],
                400.00,
                "revenu_autre",
                "Conseil technique",
                "Facture client Y",
                date_at(55),
            )
        )

        # --- Remboursements ---
        transactions.append(
            (
                acct_bnp,
                cat_ids["Remboursements"],
                38.50,
                "remboursement",
                "Remboursement Secu",
                "Consultation medecin",
                date_at(40),
            )
        )
        transactions.append(
            (
                acct_bnp,
                cat_ids["Remboursements"],
                120.00,
                "remboursement",
                "Remboursement assurance",
                "Sinistre auto",
                date_at(15),
            )
        )

        # --- Epargne vers livret A (solde cible ~8 500 EUR) ---
        # Solde initial historique
        transactions.append(
            (
                acct_livret,
                cat_ids["Autres revenus"],
                7600.00,
                "virement",
                "Solde reporte",
                "Epargne accumulee",
                date_at(89),
            )
        )
        # Virements mensuels
        for m in range(3):
            d_offset = 8 + 30 * m
            transactions.append(
                (
                    acct_livret,
                    cat_ids["Autres revenus"],
                    300.00,
                    "virement",
                    "Virement epargne",
                    "Epargne mensuelle",
                    date_at(d_offset),
                )
            )

        # Insertion de toutes les transactions
        tx_count = 0
        for acct, cat, montant, type_tx, libelle, notes, dt in transactions:
            cursor.execute(
                """
                INSERT INTO transactions (
                    user_id, account_id, category_id,
                    montant, type_transaction, libelle, notes,
                    date_heure_transaction, frais_transaction,
                    statut, devise,
                    date_creation, date_mise_a_jour
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    user_id,
                    acct,
                    cat,
                    montant,
                    type_tx,
                    libelle,
                    notes,
                    dt,
                    0,
                    "comptabilise",
                    "EUR",
                    now_iso,
                    now_iso,
                ),
            )
            tx_count += 1

        print(f"   {tx_count} transactions creees.")

        # ------------------------------------------------------------------
        # 5. Mise a jour des soldes des comptes
        # ------------------------------------------------------------------
        print("\nCalcul des soldes des comptes...")

        for acct_id in account_ids:
            cursor.execute(
                "SELECT COALESCE(SUM(montant), 0) FROM transactions WHERE account_id = %s AND user_id = %s",
                (acct_id, user_id),
            )
            solde = cursor.fetchone()[0]
            cursor.execute(
                'UPDATE "ComptesBancaires" SET solde_actuel = %s WHERE id_compte = %s',
                (solde, acct_id),
            )
            cursor.execute(
                'SELECT nom_banque FROM "ComptesBancaires" WHERE id_compte = %s',
                (acct_id,),
            )
            nom = cursor.fetchone()[0]
            print(f"   {nom} : {solde:+.2f} EUR")

        # ------------------------------------------------------------------
        # 6. Budgets mensuels
        # ------------------------------------------------------------------
        print("\nCreation des budgets...")

        start_date = today.replace(day=1).isoformat()

        budgets_def = [
            ("Alimentation", 600.00),
            ("Transport", 200.00),
            ("Logement", 1000.00),
            ("Loisirs", 300.00),
            ("Restaurants", 200.00),
            ("Abonnements", 80.00),
        ]

        for cat_name, amount in budgets_def:
            cursor.execute(
                """
                INSERT INTO budgets (
                    user_id, category_id, amount, spent_amount,
                    period, start_date,
                    notification_threshold,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    user_id,
                    cat_ids[cat_name],
                    amount,
                    0.00,
                    "monthly",
                    start_date,
                    80,
                    now_iso,
                    now_iso,
                ),
            )
            print(f"   Budget '{cat_name}' : {amount:.0f} EUR/mois")

        # ------------------------------------------------------------------
        # Commit
        # ------------------------------------------------------------------
        conn.commit()

        # ------------------------------------------------------------------
        # Resume
        # ------------------------------------------------------------------
        print("\n" + "=" * 50)
        print("Compte demo cree avec succes !")
        print("=" * 50)
        print(f"\n   Email    : {DEMO_EMAIL}")
        print("   Password : (defini via la variable d'environnement DEMO_PASSWORD)")
        print(f"\n   Comptes  : {len(account_ids)}")
        print(f"   Categories: {len(cat_ids)}")
        print(f"   Transactions: {tx_count}")
        print(f"   Budgets  : {len(budgets_def)}")
        print(f"\n   Connexion : https://example.com/auth/login")
        print()

        return True

    except Exception as e:
        print(f"\nERREUR : {e}")
        conn.rollback()
        import traceback

        traceback.print_exc()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    create_demo_user()
