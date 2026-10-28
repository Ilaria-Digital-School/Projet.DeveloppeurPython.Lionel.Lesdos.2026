"""
Services liés aux opérations sur les transactions pour le tableau de bord.
"""

import logging
from datetime import datetime

from sqlalchemy import func

from core.extensions import db
from core.models.transactions import Transaction, TransactionType

logger = logging.getLogger(__name__)


class DashboardTransactionService:
    """Service pour les opérations sur les transactions du tableau de bord"""

    @staticmethod
    def get_recent_transactions(user_id: int, limit: int = 5) -> list:
        """
        Recupere les transactions recentes d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            limit: Nombre maximum de transactions a retourner

        Returns:
            list: Liste d'objets Transaction
        """
        try:
            transactions = (
                Transaction.query.filter(Transaction.user_id == user_id)
                .order_by(
                    Transaction.date_heure_transaction.desc(),
                    Transaction.date_creation.desc(),
                )
                .limit(limit)
                .all()
            )

            return transactions

        except Exception as e:
            logger.error(
                f"Erreur recuperation transactions recentes: {e}", exc_info=True
            )
            return []

    @staticmethod
    def get_transactions_for_period(user_id: int, start_date, end_date) -> list:
        """
        Recupere les transactions pour une periode donnee.

        Args:
            user_id: ID de l'utilisateur
            start_date: Date de debut
            end_date: Date de fin

        Returns:
            list: Liste d'objets Transaction
        """
        try:
            transactions = (
                Transaction.query.filter(
                    Transaction.user_id == user_id,
                    Transaction.date_heure_transaction >= start_date,
                    Transaction.date_heure_transaction <= end_date,
                )
                .order_by(Transaction.date_heure_transaction.desc())
                .all()
            )

            return transactions

        except Exception as e:
            logger.error(
                f"Erreur recuperation transactions periode: {e}", exc_info=True
            )
            return []

    @staticmethod
    def get_monthly_totals(
        user_id: int, start_date: datetime, end_date: datetime
    ) -> tuple[float, float]:
        """
        Calcule le total des dépenses et revenus pour une période donnée.

        Args:
            user_id: ID de l'utilisateur
            start_date: Date de début
            end_date: Date de fin

        Returns:
            tuple: (total_depenses, total_revenus)
        """
        try:
            # Requête optimisée avec une seule jointure
            result = (
                db.session.query(
                    Transaction.type_transaction,
                    func.sum(Transaction.montant).label("total"),
                )
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.date_heure_transaction.between(start_date, end_date),
                )
                .group_by(Transaction.type_transaction)
                .all()
            )

            expense_types = TransactionType.expense_values()
            income_types = TransactionType.income_values()
            expenses = sum(
                float(r.total) for r in result if r.type_transaction in expense_types
            )
            income = sum(
                float(r.total) for r in result if r.type_transaction in income_types
            )

            return expenses, income

        except Exception as e:
            logger.error(
                f"Erreur lors du calcul des totaux mensuels: {str(e)}", exc_info=True
            )
            return 0.0, 0.0
