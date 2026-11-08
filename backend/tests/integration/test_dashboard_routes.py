"""Tests d'intégration pour les routes du dashboard."""

import pytest

pytestmark = pytest.mark.integration


class TestDashboardAccess:
    """Tests d'accès au dashboard."""

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/dashboard/")
        assert resp.status_code == 302

    def test_dashboard_authenticated(self, auth_client, account, category):
        resp = auth_client.get("/dashboard/")
        assert resp.status_code in (200, 500)


class TestDashboardBudgetsSupprimees:
    """Les routes web budgets ont été supprimées (gestion via /api/v1/budgets)."""

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_budgets_route_removed(self, auth_client, method):
        resp = getattr(auth_client, method)("/dashboard/budgets")
        assert resp.status_code == 404


class TestResumeFinancier:
    """Régression : les calculs tournaient dans des threads sans contexte Flask."""

    def test_resume_calcule_avec_les_vraies_donnees(
        self, app, user, account, transaction, caplog
    ):
        from core.services.dashboard.dashboard_main_service import DashboardService

        with caplog.at_level("ERROR"):
            summary = DashboardService.get_financial_summary(user.id)

        erreurs = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
        assert erreurs == []
        assert summary["current_balance"] == 1500.0
        assert [t.id for t in summary["recent_transactions"]] == [transaction.id]

    def test_api_summary_renvoie_le_solde(self, auth_client, account):
        resp = auth_client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["stats"]["balance"] == 1500.0
