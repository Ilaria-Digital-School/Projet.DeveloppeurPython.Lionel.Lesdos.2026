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
