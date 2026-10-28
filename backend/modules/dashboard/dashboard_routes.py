"""
Routes pour le module de tableau de bord

Ce module définit les routes pour l'interface utilisateur du tableau de bord
et les API associées. Implémentation complète utilisant les services métier.
"""

import logging
from datetime import datetime

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from core.extensions import db
from core.models.category import Category
from core.services.admin.admin_services import AdminService
from core.services.dashboard.dashboard_transaction_service import (
    DashboardTransactionService,
)

from . import dashboard_bp

logger = logging.getLogger(__name__)


@dashboard_bp.route("/")
@login_required
def dashboard():
    """
    Version simplifiée du dashboard utilisant directement les modèles de données
    """
    try:
        user_id = current_user.id
        logger.info(f"🏠 Dashboard principal - Utilisateur: {user_id}")

        # Utilisation directe de requêtes SQL pour compatibilité avec la base
        from sqlalchemy import text

        # Calcul du solde total depuis la table ComptesBancaires
        result = db.session.execute(
            text("""
            SELECT COALESCE(SUM(solde_actuel), 0) 
            FROM "ComptesBancaires" 
            WHERE utilisateur_id = :user_id AND est_actif = true
        """),
            {"user_id": user_id},
        )
        total_balance = float(result.scalar() or 0.0)

        # Calcul des dépenses et revenus du mois depuis la table transactions
        start_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")

        # Dépenses du mois (types: achat, retrait, etc.)
        result = db.session.execute(
            text("""
            SELECT COALESCE(SUM(montant), 0) 
            FROM transactions 
            WHERE user_id = :user_id 
            AND date_heure_transaction >= :start_date
            AND type_transaction IN ('achat', 'ACHAT', 'retrait', 'RETRAIT', 'expense')
        """),
            {"user_id": user_id, "start_date": start_of_month},
        )
        monthly_expenses = float(result.scalar() or 0.0)

        # Revenus du mois (types: salaire, dépôt, etc.)
        result = db.session.execute(
            text("""
            SELECT COALESCE(SUM(montant), 0) 
            FROM transactions 
            WHERE user_id = :user_id 
            AND date_heure_transaction >= :start_date
            AND type_transaction IN ('salaire', 'SALAIRE', 'depot', 'DEPOT', 'income')
        """),
            {"user_id": user_id, "start_date": start_of_month},
        )
        monthly_income = float(result.scalar() or 0.0)

        # Calcul de l'objectif mensuel (somme des budgets actifs du mois en cours)
        current_date = datetime.now().date()
        result = db.session.execute(
            text("""
            SELECT COALESCE(SUM(amount), 0) 
            FROM budgets 
            WHERE user_id = :user_id 
            AND start_date <= :current_date 
            AND (end_date >= :current_date OR end_date IS NULL)
            AND period = 'monthly'
        """),
            {"user_id": user_id, "current_date": current_date},
        )
        total_budget_amount = float(result.scalar() or 0.0)

        # Transactions récentes (5 dernières)
        result = db.session.execute(
            text("""
            SELECT t.id, t.montant, t.libelle, t.date_heure_transaction, c.name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = :user_id
            ORDER BY t.date_heure_transaction DESC
            LIMIT 5
        """),
            {"user_id": user_id},
        )
        recent_transactions_data = result.fetchall()

        # Préparer les données pour le template
        dashboard_data = {
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
            },
            "stats": {
                "balance": float(total_balance),
                "total_depenses": float(monthly_expenses),
                "total_revenus": float(monthly_income),
                "total_budget_amount": float(total_budget_amount),
            },
            "recent_transactions": [
                {
                    "id": t[0],
                    "amount": float(t[1]),
                    "description": t[2],
                    "transaction_date": (
                        str(t[3])[:10] if t[3] else datetime.now().strftime("%Y-%m-%d")
                    ),
                    "category_name": t[4] if t[4] else "Sans catégorie",
                    "icon": (
                        "fas fa-arrow-up text-green-600"
                        if float(t[1]) > 0
                        else "fas fa-arrow-down text-red-600"
                    ),
                }
                for t in recent_transactions_data
            ],
        }

        # Ajouter les statistiques admin si l'utilisateur est admin
        if current_user.is_admin:
            try:
                admin_dashboard_stats = AdminService.get_dashboard_stats()
                dashboard_data["admin_stats"] = {
                    "users_count": admin_dashboard_stats.get("users", {}).get(
                        "total", 0
                    ),
                    "new_users_week": admin_dashboard_stats.get("users", {}).get(
                        "new_week", 0
                    ),
                    "total_volume": admin_dashboard_stats.get("financial", {}).get(
                        "total_volume", 0
                    ),
                    "transactions_count": admin_dashboard_stats.get(
                        "transactions", {}
                    ).get("total", 0),
                    "suspicious_count": len(
                        AdminService.get_suspicious_transactions(limit=10)
                    ),
                }
            except Exception as admin_err:
                logger.warning(f"⚠️ Erreur stats admin: {admin_err}")
                dashboard_data["admin_stats"] = None

        logger.info(
            f"✅ Dashboard simplifié chargé - Balance: {total_balance}€, Dépenses: {monthly_expenses}€, Revenus: {monthly_income}€"
        )

        return render_template("dashboard.html", **dashboard_data)

    except Exception as e:
        logger.error(f"❌ Erreur Dashboard: {str(e)}", exc_info=True)

        # En cas d'erreur, retourner des données par défaut
        error_data = {
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
            },
            "stats": {
                "balance": 0.0,
                "total_depenses": 0.0,
                "total_revenus": 0.0,
                "total_budget_amount": 0.0,
            },
            "recent_transactions": [],
            "error_message": f"Erreur: {str(e)}",
        }

        return render_template("dashboard.html", **error_data)


@dashboard_bp.route("/transactions")
@login_required
def transactions():
    """
    Page de gestion des transactions

    Returns:
        Template HTML ou redirection
    """
    try:
        user_id = current_user.id
        logger.info(f"💳 Page Transactions - Utilisateur: {user_id}")

        # Récupérer les transactions via le service
        transactions_data = DashboardTransactionService.get_recent_transactions(
            user_id=user_id, limit=50  # Plus de transactions pour la page dédiée
        )

        # Récupérer les catégories pour le formulaire
        categories = db.session.query(Category).order_by(Category.name).all()

        return render_template(
            "transactions.html", transactions=transactions_data, categories=categories
        )

    except Exception as e:
        logger.error(f"❌ Erreur page Transactions: {str(e)}", exc_info=True)
        flash(f"Erreur: {str(e)}", "error")
        return redirect(url_for("dashboard_bp.dashboard"))


@dashboard_bp.route("/categories")
@login_required
def categories():
    """
    Page de gestion des catégories

    Returns:
        Template HTML ou redirection
    """
    try:
        user_id = current_user.id
        logger.info(f"📁 Page Catégories - Utilisateur: {user_id}")

        # Récupérer les catégories
        categories_data = (
            db.session.query(Category)
            .order_by(Category.is_expense.desc(), Category.name)
            .all()
        )

        return render_template("categories.html", categories=categories_data)

    except Exception as e:
        logger.error(f"❌ Erreur page Catégories: {str(e)}", exc_info=True)
        flash(f"Erreur: {str(e)}", "error")
        return redirect(url_for("dashboard_bp.dashboard"))


@dashboard_bp.route("/profile")
@login_required
def profile():
    """
    Page de profil utilisateur dans le contexte du dashboard

    Returns:
        Redirection vers le module de profil
    """
    # Rediriger vers le module de profil dédié
    return redirect(url_for("profile_bp.profile"))
