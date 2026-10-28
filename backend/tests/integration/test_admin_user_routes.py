"""Tests d'intégration pour les routes admin de la vue utilisateurs enrichie."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

pytestmark = pytest.mark.integration


class TestAdminEndpointsProtection:
    """Protection des 3 nouveaux endpoints admin (auth + rôle admin)."""

    ROUTES = [
        "/api/v1/admin/users/1/activity",
        "/api/v1/admin/users/1/accounts",
        "/api/v1/admin/users/1/transactions",
    ]

    def test_anonymous_denied(self, client):
        for route in self.ROUTES:
            resp = client.get(route)
            assert resp.status_code in (302, 401), route

    def test_non_admin_forbidden(self, auth_client, user):
        for route in self.ROUTES:
            resp = auth_client.get(route)
            assert resp.status_code == 403, route


class TestAdminUserActivity:
    """Tests de GET /api/v1/admin/users/<id>/activity."""

    def test_activity_includes_transaction(self, admin_client, user, transaction):
        resp = admin_client.get(f"/api/v1/admin/users/{user.id}/activity")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        types = [item["type"] for item in data["activity"]]
        assert "transaction" in types
        tx_item = next(i for i in data["activity"] if i["type"] == "transaction")
        assert tx_item["title"] == "Courses Carrefour"
        assert "date_display" in tx_item

    def test_activity_user_not_found(self, admin_client):
        resp = admin_client.get("/api/v1/admin/users/999999/activity")
        assert resp.status_code == 404

    def test_activity_limit_capped(self, admin_client, user):
        resp = admin_client.get(f"/api/v1/admin/users/{user.id}/activity?limit=500")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["activity"]) <= 50


class TestAdminUserAccounts:
    """Tests de GET /api/v1/admin/users/<id>/accounts."""

    def test_accounts_ok(self, admin_client, user, account):
        resp = admin_client.get(f"/api/v1/admin/users/{user.id}/accounts")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        accounts = data["accounts"]
        assert len(accounts) == 1
        acc = accounts[0]
        assert acc["name"] == "Compte Courant Test"
        assert acc["balance"] == 1500.0
        assert acc["currency"] == "EUR"

    def test_accounts_no_sensitive_fields(self, admin_client, user, account):
        """Minimisation : iban, account_number, bic_swift et notes non exposés."""
        resp = admin_client.get(f"/api/v1/admin/users/{user.id}/accounts")
        assert resp.status_code == 200
        acc = resp.get_json()["accounts"][0]
        assert "iban" not in acc
        assert "account_number" not in acc
        assert "bic_swift" not in acc
        assert "notes" not in acc

    def test_accounts_user_not_found(self, admin_client):
        resp = admin_client.get("/api/v1/admin/users/999999/accounts")
        assert resp.status_code == 404


class TestAdminUserTransactions:
    """Tests de GET /api/v1/admin/users/<id>/transactions."""

    def test_transactions_structure(self, admin_client, user, transaction):
        resp = admin_client.get(f"/api/v1/admin/users/{user.id}/transactions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "pagination" in data
        assert data["pagination"]["total"] == 1
        assert data["pagination"]["page"] == 1
        item = data["data"][0]
        assert item["libelle"] == "Courses Carrefour"
        assert item["montant"] == 42.5
        assert item["account_name"] == "Compte Courant Test"

    def test_transactions_pagination_page_2(
        self, admin_client, db_session, user, account, category
    ):
        from core.models.transactions import Transaction

        base_dt = datetime.now(timezone.utc)
        for i in range(3):
            db_session.add(
                Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    category_id=category.id,
                    montant=Decimal("10.00") + i,
                    type_transaction="achat",
                    libelle=f"Achat {i}",
                    date_heure_transaction=base_dt - timedelta(days=i),
                    statut="comptabilise",
                    devise="EUR",
                )
            )
        db_session.flush()

        resp = admin_client.get(
            f"/api/v1/admin/users/{user.id}/transactions?page=2&per_page=2"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["pagination"]["total"] == 3
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["pages"] == 2
        assert len(data["data"]) == 1
        # Tri desc : page 2 contient la transaction la plus ancienne
        assert data["data"][0]["libelle"] == "Achat 2"

    def test_transactions_user_not_found(self, admin_client):
        resp = admin_client.get("/api/v1/admin/users/999999/transactions")
        assert resp.status_code == 404


class TestAdminWebPagesEnriched:
    """Non-régression du rendu Jinja des pages admin enrichies."""

    def test_users_management_page(self, admin_client, user, account, transaction):
        resp = admin_client.get("/admin/users-management")
        assert resp.status_code == 200

    def test_user_details_page(self, admin_client, user, account, transaction):
        resp = admin_client.get(f"/admin/user/{user.id}")
        assert resp.status_code == 200


class TestNoSensitiveData:
    """Aucune donnée sensible dans les réponses des nouveaux endpoints."""

    def test_no_secrets_in_responses(self, admin_client, user, account, transaction):
        routes = [
            f"/api/v1/admin/users/{user.id}/activity",
            f"/api/v1/admin/users/{user.id}/accounts",
            f"/api/v1/admin/users/{user.id}/transactions",
        ]
        for route in routes:
            resp = admin_client.get(route)
            assert resp.status_code == 200, route
            body = resp.get_data(as_text=True)
            assert "password_hash" not in body, route
            assert "two_factor_secret" not in body, route
