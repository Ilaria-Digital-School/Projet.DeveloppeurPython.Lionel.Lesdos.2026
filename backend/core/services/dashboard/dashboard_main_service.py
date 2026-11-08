"""
Service principal du tableau de bord qui agrège les données des autres services.
"""

import logging
from datetime import datetime, timezone

# Import des services
from .dashboard_account_service import DashboardAccountService
from .dashboard_analytics_service import DashboardAnalyticsService
from .dashboard_budget_service import DashboardBudgetService
from .dashboard_transaction_service import DashboardTransactionService

logger = logging.getLogger(__name__)


class DashboardService:
    """Service principal pour le tableau de bord"""

    @staticmethod
    def get_financial_summary(
        user_id: int, start_date: datetime = None, end_date: datetime = None
    ) -> dict:
        """
        Récupère un résumé complet des données financières pour le tableau de bord.

        Exemple d'utilisation:
            summary = DashboardService.get_financial_summary(
                current_user.id,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 1, 31)
            )
            print(f"Solde actuel: {summary['current_balance']}€")

        Args:
            user_id: ID de l'utilisateur
            start_date: Date de début (optionnel)
            end_date: Date de fin (optionnel, par défaut aujourd'hui)

        Returns:
            dict: Dictionnaire contenant toutes les données du tableau de bord
        """
        try:
            # Définition des dates par défaut si non spécifiées
            today = datetime.now(timezone.utc).date()
            if not end_date:
                end_date = today
            if not start_date:
                start_date = end_date.replace(day=1)  # Début du mois en cours

            # Calculs séquentiels : la session SQLAlchemy et le contexte Flask
            # sont liés au thread de la requête (un ThreadPoolExecutor les perd)
            current_balance = DashboardAccountService.get_total_balance(user_id)
            recent_transactions = DashboardTransactionService.get_recent_transactions(
                user_id, 5
            )
            monthly_expenses, monthly_income = (
                DashboardTransactionService.get_monthly_totals(
                    user_id, start_date, end_date
                )
            )
            budget_goal = DashboardBudgetService.get_budget_goal(user_id, end_date)
            expenses_by_category = DashboardAnalyticsService.get_expenses_by_category(
                user_id, start_date, end_date, 5
            )
            monthly_expenses_data = DashboardAnalyticsService.get_monthly_expenses(
                user_id, 6
            )
            upcoming_budgets = DashboardBudgetService.get_upcoming_budgets(user_id, 5)

            # Construction du dictionnaire de résultat
            return {
                "current_balance": current_balance,
                "monthly_expenses": monthly_expenses,
                "monthly_income": monthly_income,
                "budget_goal": round(budget_goal, 1),
                "recent_transactions": recent_transactions,
                "expenses_by_category": expenses_by_category,
                "monthly_expenses_data": monthly_expenses_data,
                "upcoming_budgets": upcoming_budgets,
            }

        except Exception as e:
            logger.error(
                f"Erreur lors de la génération du résumé financier: {str(e)}",
                exc_info=True,
            )
            # Retourne un dictionnaire vide en cas d'erreur
            return {
                "current_balance": 0.0,
                "monthly_expenses": 0.0,
                "monthly_income": 0.0,
                "budget_goal": 0.0,
                "recent_transactions": [],
                "expenses_by_category": [],
                "monthly_expenses_data": [],
                "upcoming_budgets": [],
            }
