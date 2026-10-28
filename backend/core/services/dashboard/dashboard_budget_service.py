"""
Services liés aux opérations sur les budgets pour le tableau de bord.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_

from core.extensions import db

# Import direct du modèle Budget (évite conflit SQLAlchemy)
from core.models.budget import Budget

logger = logging.getLogger(__name__)


class DashboardBudgetService:
    """Service pour les opérations sur les budgets du tableau de bord"""

    @staticmethod
    def get_budget_goal(user_id: int, end_date: datetime) -> float:
        """
        Calcule le pourcentage d'utilisation du budget.

        Exemple d'utilisation:
            goal = DashboardBudgetService.get_budget_goal(current_user.id, datetime.now())
            print(f"Objectif: {goal}%")

        Args:
            user_id: ID de l'utilisateur
            end_date: Date de fin pour le calcul

        Returns:
            float: Pourcentage d'utilisation du budget (0-100)
        """
        try:
            # Calcul du total des budgets actifs
            total_budget = (
                db.session.query(func.sum(Budget.amount))
                .filter(
                    Budget.user_id == user_id,
                    Budget.start_date <= end_date,
                    or_(
                        Budget.end_date.is_(None),
                        Budget.end_date
                        >= end_date - timedelta(days=30),  # Derniers 30 jours
                    ),
                )
                .scalar()
                or 0.0
            )

            if total_budget <= 0:
                return 0.0

            # Calcul des dépenses du mois
            from .dashboard_transaction_service import DashboardTransactionService

            expenses, _ = DashboardTransactionService.get_monthly_totals(
                user_id, end_date.replace(day=1), end_date  # Début du mois
            )

            # Calcul du pourcentage (limité à 100%)
            return min(100.0, (expenses / float(total_budget)) * 100)

        except Exception as e:
            logger.error(
                f"Erreur lors du calcul de l'objectif budgétaire: {str(e)}",
                exc_info=True,
            )
            return 0.0

    @staticmethod
    def get_recent_budgets(user_id: int, limit: int = 5) -> list:
        """
        Recupere les budgets recents (actifs ou termines recemment).

        Args:
            user_id: ID de l'utilisateur
            limit: Nombre maximum de budgets a retourner

        Returns:
            list: Liste d'objets Budget
        """
        try:
            datetime.now(timezone.utc).date()

            budgets = (
                Budget.query.filter(
                    Budget.user_id == user_id,
                )
                .order_by(Budget.start_date.desc())
                .limit(limit)
                .all()
            )

            return budgets

        except Exception as e:
            logger.error(f"Erreur recuperation budgets recents: {e}", exc_info=True)
            return []

    @staticmethod
    def get_active_budgets(user_id: int, reference_date=None) -> list:
        """
        Recupere les budgets actifs a une date donnee.

        Args:
            user_id: ID de l'utilisateur
            reference_date: Date de reference (defaut: aujourd'hui)

        Returns:
            list: Liste d'objets Budget
        """
        try:
            if not reference_date:
                reference_date = datetime.now(timezone.utc).date()

            budgets = (
                Budget.query.filter(
                    Budget.user_id == user_id,
                    Budget.start_date <= reference_date,
                    or_(Budget.end_date.is_(None), Budget.end_date >= reference_date),
                )
                .order_by(Budget.start_date.desc())
                .all()
            )

            return budgets

        except Exception as e:
            logger.error(f"Erreur recuperation budgets actifs: {e}", exc_info=True)
            return []

    @staticmethod
    def get_upcoming_budgets(user_id: int, limit: int = 5) -> list:
        """
        Récupère les budgets à échéance proche.

        Args:
            user_id: ID de l'utilisateur
            limit: Nombre maximum de budgets à retourner

        Returns:
            list: Liste des budgets formatés avec leur progression
        """
        try:
            today = datetime.now(timezone.utc).date()

            budgets = (
                Budget.query.filter(Budget.user_id == user_id, Budget.end_date >= today)
                .order_by(Budget.end_date.asc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": b.id,
                    "name": b.category.name if b.category else "Sans nom",
                    "category_name": (
                        b.category.name if b.category else "Non catégorisé"
                    ),
                    "amount": float(b.amount),
                    "start_date": b.start_date.isoformat(),
                    "end_date": b.end_date.isoformat() if b.end_date else None,
                    "progress": min(
                        100,
                        (b.get_used_amount() / b.amount * 100) if b.amount > 0 else 0,
                    ),
                }
                for b in budgets
            ]

        except Exception as e:
            logger.error(
                f"Erreur lors de la récupération des budgets: {str(e)}", exc_info=True
            )
            return []
