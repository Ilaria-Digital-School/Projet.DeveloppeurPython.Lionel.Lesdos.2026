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

            # Calcul des données en parallèle pour de meilleures performances
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=4) as executor:
                # Solde total
                balance_future = executor.submit(
                    DashboardAccountService.get_total_balance, user_id
                )

                # Transactions récentes
                transactions_future = executor.submit(
                    DashboardTransactionService.get_recent_transactions,
                    user_id,
                    5,  # Limite à 5 transactions
                )

                # Dépenses et revenus du mois
                totals_future = executor.submit(
                    DashboardTransactionService.get_monthly_totals,
                    user_id,
                    start_date,
                    end_date,
                )

                # Objectif budgétaire
                budget_goal_future = executor.submit(
                    DashboardBudgetService.get_budget_goal, user_id, end_date
                )

                # Dépenses par catégorie
                expenses_by_category_future = executor.submit(
                    DashboardAnalyticsService.get_expenses_by_category,
                    user_id,
                    start_date,
                    end_date,
                    5,  # Top 5 catégories
                )

                # Historique des dépenses
                monthly_expenses_future = executor.submit(
                    DashboardAnalyticsService.get_monthly_expenses,
                    user_id,
                    6,  # 6 derniers mois
                )

                # Budgets à venir
                upcoming_budgets_future = executor.submit(
                    DashboardBudgetService.get_upcoming_budgets,
                    user_id,
                    5,  # Prochains 5 budgets
                )

                # Récupération des résultats
                current_balance = balance_future.result()
                recent_transactions = transactions_future.result()
                monthly_expenses, monthly_income = totals_future.result()
                budget_goal = budget_goal_future.result()
                expenses_by_category = expenses_by_category_future.result()
                monthly_expenses_data = monthly_expenses_future.result()
                upcoming_budgets = upcoming_budgets_future.result()

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
