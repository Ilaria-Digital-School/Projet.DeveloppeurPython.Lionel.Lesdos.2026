"""
Services liés aux comptes pour le tableau de bord.
"""

import logging

from sqlalchemy import func

from core.extensions import db
from core.models.account import Account

logger = logging.getLogger(__name__)


class DashboardAccountService:
    """Service pour les opérations sur les comptes du tableau de bord"""

    @staticmethod
    def get_total_balance(user_id: int) -> float:
        """
        Calcule le solde total de tous les comptes actifs d'un utilisateur.

        Exemple d'utilisation:
            balance = DashboardAccountService.get_total_balance(current_user.id)
            print(f"Solde total: {balance}€")

        Args:
            user_id: ID de l'utilisateur

        Returns:
            float: Solde total
        """
        try:
            # Requête optimisée pour obtenir uniquement la somme des soldes
            total = (
                db.session.query(func.sum(Account._balance_db))
                .filter(Account.user_id == user_id, Account._is_active_db == True)
                .scalar()
            )

            return float(total or 0.0)

        except Exception as e:
            logger.error(
                f"Erreur lors du calcul du solde total: {str(e)}", exc_info=True
            )
            return 0.0
