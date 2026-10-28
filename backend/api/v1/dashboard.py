"""
API REST v1 — Dashboard.

Routes:
    GET    /api/v1/dashboard/summary              Résumé du tableau de bord
    GET    /api/v1/dashboard/export                Exporter les données du dashboard
    POST   /api/v1/dashboard/preferences           Mettre à jour les préférences
    GET    /api/v1/dashboard/charts/balance-evolution     Graphique évolution des soldes
    GET    /api/v1/dashboard/charts/expenses-breakdown    Graphique répartition dépenses
    GET    /api/v1/dashboard/charts/income-vs-expenses    Graphique revenus vs dépenses
    GET    /api/v1/dashboard/charts/budget-progress       Graphique progression budgets
    GET    /api/v1/dashboard/charts/kpis                  KPIs du dashboard
"""

import logging
from datetime import datetime

from flask import request
from flask_login import current_user, login_required

from core.services.chart_service import ChartService
from core.services.dashboard.dashboard_analytics_service import (
    DashboardAnalyticsService,
)
from core.services.dashboard.dashboard_budget_service import DashboardBudgetService
from core.services.dashboard.dashboard_main_service import DashboardService
from core.services.dashboard.dashboard_transaction_service import (
    DashboardTransactionService,
)

from . import api_v1_bp
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


@api_v1_bp.route("/dashboard/summary", methods=["GET"])
@login_required
def v1_dashboard_summary():
    """Résumé du tableau de bord."""
    try:
        user_id = current_user.id
        today = datetime.now().date()
        start_date = today.replace(day=1)

        financial_summary = DashboardService.get_financial_summary(
            user_id=user_id, start_date=start_date, end_date=today
        )

        recent_transactions = DashboardTransactionService.get_recent_transactions(
            user_id=user_id, limit=5
        )

        recent_budgets = DashboardBudgetService.get_recent_budgets(
            user_id=user_id, limit=5
        )

        expenses_by_category = DashboardAnalyticsService.get_expenses_by_category(
            user_id=user_id, start_date=start_date, end_date=today, limit=5
        )

        summary_data = {
            "stats": {
                "budget_count": financial_summary.get("budget_count", 0),
                "total_budget": financial_summary.get("total_budget", 0),
                "monthly_income": financial_summary.get("monthly_income", 0),
                "monthly_expenses": financial_summary.get("monthly_expenses", 0),
                "balance": financial_summary.get("balance", 0),
            },
            "recent_transactions": [
                {
                    "id": t.id,
                    "amount": float(t.montant) if t.montant else 0,
                    "description": t.libelle or "",
                    "date": (
                        t.date_heure_transaction.strftime("%Y-%m-%d")
                        if t.date_heure_transaction
                        else ""
                    ),
                    "category": (
                        t.category.name
                        if hasattr(t, "category") and t.category
                        else "Sans catégorie"
                    ),
                }
                for t in recent_transactions
            ],
            "budgets": [
                {
                    "id": b.id,
                    "amount": float(b.amount),
                    "spent": float(b.spent_amount or 0),
                    "category": b.category.name if b.category else "Sans catégorie",
                    "period": b.period,
                }
                for b in recent_budgets
            ],
            "expenses_by_category": expenses_by_category,
        }

        return api_success(summary_data)

    except Exception as e:
        logger.error(f"Erreur API Dashboard Summary: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/dashboard/export", methods=["GET"])
@login_required
def v1_dashboard_export():
    """Exporte les données du tableau de bord."""
    try:
        user_id = current_user.id
        today = datetime.now().date()
        start_date = today.replace(day=1)

        financial_summary = DashboardService.get_financial_summary(
            user_id=user_id, start_date=start_date, end_date=today
        )

        transactions = DashboardTransactionService.get_transactions_for_period(
            user_id=user_id, start_date=start_date, end_date=today
        )

        budgets = DashboardBudgetService.get_active_budgets(
            user_id=user_id, reference_date=today
        )

        export_data = {
            "export_date": datetime.now().isoformat(),
            "stats": {
                "budget_count": financial_summary.get("budget_count", 0),
                "total_budget": financial_summary.get("total_budget", 0),
                "monthly_income": financial_summary.get("monthly_income", 0),
                "monthly_expenses": financial_summary.get("monthly_expenses", 0),
                "balance": financial_summary.get("balance", 0),
            },
            "transactions": [
                {
                    "id": t.id,
                    "amount": float(t.montant) if t.montant else 0,
                    "description": t.libelle or "",
                    "date": (
                        t.date_heure_transaction.strftime("%Y-%m-%d")
                        if t.date_heure_transaction
                        else ""
                    ),
                    "category": (
                        t.category.name
                        if hasattr(t, "category") and t.category
                        else "Sans catégorie"
                    ),
                }
                for t in transactions
            ],
            "budgets": [
                {
                    "id": b.id,
                    "amount": float(b.amount),
                    "spent": float(b.spent_amount or 0),
                    "category": b.category.name if b.category else "Sans catégorie",
                    "period": b.period,
                    "start_date": (
                        b.start_date.strftime("%Y-%m-%d") if b.start_date else ""
                    ),
                    "end_date": b.end_date.strftime("%Y-%m-%d") if b.end_date else "",
                }
                for b in budgets
            ],
        }

        return api_success(export_data)

    except Exception as e:
        logger.error(f"Erreur Export Dashboard: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/dashboard/preferences", methods=["POST"])
@login_required
def v1_dashboard_preferences():
    """Met à jour les préférences du dashboard."""
    try:
        data = request.get_json() if request.is_json else request.form

        default_view = data.get("default_view", "monthly")
        show_inactive = data.get("show_inactive", "false") == "true"
        chart_type = data.get("chart_type", "bar")

        preferences = {
            "default_view": default_view,
            "show_inactive": show_inactive,
            "chart_type": chart_type,
        }

        return api_success(
            {"preferences": preferences}, message="Préférences mises à jour avec succès"
        )

    except Exception as e:
        logger.error(f"Erreur Préférences: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# ── CHARTS ───────────────────────────────────────────────────────────────────


@api_v1_bp.route("/dashboard/charts/balance-evolution", methods=["GET"])
@login_required
def v1_chart_balance_evolution():
    """Graphique évolution des soldes."""
    try:
        user_id = current_user.id
        months = request.args.get("months", 6, type=int)
        chart_data = ChartService.get_balance_evolution(user_id, months)
        return api_success({"chart_data": chart_data})
    except Exception as e:
        logger.error(f"Erreur API Chart Balance: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/dashboard/charts/expenses-breakdown", methods=["GET"])
@login_required
def v1_chart_expenses_breakdown():
    """Graphique répartition des dépenses."""
    try:
        user_id = current_user.id
        period_days = request.args.get("period", 30, type=int)
        chart_data = ChartService.get_expenses_breakdown(user_id, period_days)
        return api_success({"chart_data": chart_data})
    except Exception as e:
        logger.error(f"Erreur API Chart Expenses: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/dashboard/charts/income-vs-expenses", methods=["GET"])
@login_required
def v1_chart_income_vs_expenses():
    """Graphique revenus vs dépenses."""
    try:
        user_id = current_user.id
        months = request.args.get("months", 12, type=int)
        chart_data = ChartService.get_income_vs_expenses(user_id, months)
        return api_success({"chart_data": chart_data})
    except Exception as e:
        logger.error(f"Erreur API Chart Income/Expenses: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/dashboard/charts/budget-progress", methods=["GET"])
@login_required
def v1_chart_budget_progress():
    """Graphique progression des budgets."""
    try:
        user_id = current_user.id
        chart_data = ChartService.get_budget_progress(user_id)
        return api_success({"chart_data": chart_data})
    except Exception as e:
        logger.error(f"Erreur API Chart Budget Progress: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/dashboard/charts/kpis", methods=["GET"])
@login_required
def v1_chart_kpis():
    """KPIs du dashboard."""
    try:
        user_id = current_user.id
        kpis = ChartService.get_dashboard_kpis(user_id)
        return api_success({"kpis": kpis})
    except Exception as e:
        logger.error(f"Erreur API Chart KPIs: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
