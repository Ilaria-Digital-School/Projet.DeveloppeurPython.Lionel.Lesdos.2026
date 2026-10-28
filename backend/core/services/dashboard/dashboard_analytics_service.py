"""
Services d'analyse de données pour le tableau de bord.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import extract, func

from core.extensions import db
from core.models.category import Category
from core.models.transactions import Transaction, TransactionType

logger = logging.getLogger(__name__)


class DashboardAnalyticsService:
    """Service pour les analyses de données du tableau de bord"""

    @staticmethod
    def get_expenses_by_category(
        user_id: int, start_date: datetime, end_date: datetime, limit: int = 5
    ) -> list:
        """
        Récupère les dépenses par catégorie.

        Exemple d'utilisation:
            expenses = DashboardAnalyticsService.get_expenses_by_category(
                current_user.id,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 31)
            )
            for expense in expenses:
                print(f"{expense['name']}: {expense['total']}€")

        Args:
            user_id: ID de l'utilisateur
            start_date: Date de début
            end_date: Date de fin
            limit: Nombre maximum de catégories à retourner

        Returns:
            list: Liste des dépenses par catégorie
        """
        try:
            # Requête optimisée avec jointure et agrégation
            results = (
                db.session.query(
                    Category.id,
                    Category.name,
                    Category.icon,
                    func.sum(Transaction.montant).label("total"),
                )
                .join(Transaction, Transaction.category_id == Category.id)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.type_transaction.in_(TransactionType.expense_values()),
                    Transaction.date_heure_transaction.between(start_date, end_date),
                )
                .group_by(Category.id, Category.name, Category.icon)
                .order_by(func.sum(Transaction.montant).desc())
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": cat_id,
                    "name": name or "Sans catégorie",
                    "icon": icon or "fa-tag",
                    "total": float(total),
                }
                for cat_id, name, icon, total in results
            ]

        except Exception as e:
            logger.error(
                f"Erreur lors du calcul des dépenses par catégorie: {str(e)}",
                exc_info=True,
            )
            return []

    @staticmethod
    def get_monthly_expenses(user_id: int, months: int = 6) -> list:
        """
        Récupère l'historique des dépenses sur plusieurs mois.

        Args:
            user_id: ID de l'utilisateur
            months: Nombre de mois à inclure

        Returns:
            list: Liste des dépenses mensuelles formatées
        """
        try:
            end_date = datetime.now(timezone.utc).date()
            start_date = (end_date - timedelta(days=30 * months)).replace(day=1)

            # Requête optimisée avec agrégation par mois/année
            results = (
                db.session.query(
                    extract("year", Transaction.date_heure_transaction).label("year"),
                    extract("month", Transaction.date_heure_transaction).label("month"),
                    func.sum(Transaction.montant).label("total"),
                )
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.type_transaction.in_(TransactionType.expense_values()),
                    Transaction.date_heure_transaction.between(start_date, end_date),
                )
                .group_by(
                    extract("year", Transaction.date_heure_transaction),
                    extract("month", Transaction.date_heure_transaction),
                )
                .order_by(
                    extract("year", Transaction.date_heure_transaction).desc(),
                    extract("month", Transaction.date_heure_transaction).desc(),
                )
                .limit(months)
                .all()
            )

            return [
                {
                    "year": int(year),
                    "month": int(month),
                    "total": float(total or 0),
                    "month_name": datetime(int(year), int(month), 1).strftime("%b %Y"),
                }
                for year, month, total in results
            ]

        except Exception as e:
            logger.error(
                f"Erreur lors de la récupération de l'historique des dépenses: {str(e)}",
                exc_info=True,
            )
            return []
