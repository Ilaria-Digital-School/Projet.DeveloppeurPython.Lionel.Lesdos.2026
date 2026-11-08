"""
Tests fonctionnels complets de l'application.
Verifie que les pages HTML se chargent et que les endpoints API v1 repondent.
"""

from datetime import date, datetime, timezone

import pytest

pytestmark = pytest.mark.functional


# ============================================================
# Pages WEB (HTML)
# ============================================================


class TestWebPages:
    """Verifie que les pages HTML se chargent correctement."""

    def test_login_page(self, client):
        resp = client.get("/auth/login")
        assert resp.status_code == 200
        assert b"login" in resp.data.lower() or b"connexion" in resp.data.lower()

    def test_register_page(self, client):
        resp = client.get("/auth/register")
        assert resp.status_code == 200

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/dashboard/", follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_dashboard_authenticated(self, auth_client):
        resp = auth_client.get("/dashboard/")
        assert resp.status_code == 200

    def test_accounts_page(self, auth_client):
        resp = auth_client.get("/comptes/")
        assert resp.status_code == 200

    def test_categories_page(self, auth_client):
        resp = auth_client.get("/categories/")
        assert resp.status_code == 200

    def test_transactions_page(self, auth_client):
        resp = auth_client.get("/transactions/")
        assert resp.status_code == 200


# ============================================================
# API v1 — Comptes
# ============================================================


class TestAPIAccounts:
    """Tests fonctionnels pour /api/v1/comptes"""

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/comptes")
        assert resp.status_code in (302, 401)

    def test_list_authenticated(self, auth_client, account):
        resp = auth_client.get("/api/v1/comptes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert data.get("status") == "success"

    def test_create_account(self, auth_client):
        resp = auth_client.post(
            "/api/v1/comptes",
            json={
                "name": "Nouveau Compte Test",
                "account_type": "checking",
                "initial_balance": 100.0,
                "currency": "EUR",
            },
        )
        assert resp.status_code in (200, 201)
        data = resp.get_json()
        assert data is not None

    def test_get_account(self, auth_client, account):
        resp = auth_client.get(f"/api/v1/comptes/{account.id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None


# ============================================================
# API v1 — Categories
# ============================================================


class TestAPICategories:
    """Tests fonctionnels pour /api/v1/categories"""

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/categories")
        assert resp.status_code in (302, 401)

    def test_list_authenticated(self, auth_client, category):
        resp = auth_client.get("/api/v1/categories")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert data.get("status") == "success"

    def test_create_category(self, auth_client):
        resp = auth_client.post(
            "/api/v1/categories",
            json={
                "name": "Test Catégorie",
                "is_expense": True,
                "color": "#FF0000",
                "icon": "fa-tag",
            },
        )
        assert resp.status_code in (200, 201)
        data = resp.get_json()
        assert data is not None

    def test_get_category(self, auth_client, category):
        resp = auth_client.get(f"/api/v1/categories/{category.id}")
        assert resp.status_code == 200

    def test_update_category(self, auth_client, category):
        resp = auth_client.put(
            f"/api/v1/categories/{category.id}",
            json={"name": "Alimentation Modifiée", "color": "#00FF00"},
        )
        assert resp.status_code == 200

    def test_delete_category_no_transactions(self, auth_client, db_session):
        """Supprime une categorie sans transactions liees."""
        from core.models.category import Category
        from core.models.user import User

        user = db_session.query(User).first()
        cat = Category(
            user_id=user.id,
            name="A Supprimer",
            is_expense=True,
            category_type="expense",
        )
        db_session.add(cat)
        db_session.flush()
        resp = auth_client.delete(f"/api/v1/categories/{cat.id}")
        assert resp.status_code == 200


# ============================================================
# API v1 — Transactions
# ============================================================


class TestAPITransactions:
    """Tests fonctionnels pour /api/v1/transactions"""

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/transactions")
        assert resp.status_code in (302, 401)

    def test_list_authenticated(self, auth_client, transaction):
        resp = auth_client.get("/api/v1/transactions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert data.get("status") == "success"

    def test_create_transaction(self, auth_client, account, category):
        resp = auth_client.post(
            "/api/v1/transactions",
            json={
                "account_id": account.id,
                "category_id": category.id,
                "amount": 25.50,
                "type": "achat",
                "description": "Test transaction fonctionnelle",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            },
        )
        assert resp.status_code in (200, 201)
        data = resp.get_json()
        assert data is not None

    def test_get_transaction(self, auth_client, transaction):
        resp = auth_client.get(f"/api/v1/transactions/{transaction.id}")
        assert resp.status_code == 200

    def test_delete_transaction(self, auth_client, transaction):
        resp = auth_client.delete(f"/api/v1/transactions/{transaction.id}")
        assert resp.status_code == 200


# ============================================================
# API v1 — Budgets
# ============================================================


class TestAPIBudgets:
    """Tests fonctionnels pour /api/v1/budgets"""

    def test_list_requires_auth(self, client):
        resp = client.get("/api/v1/budgets")
        assert resp.status_code in (302, 401)

    def test_list_authenticated(self, auth_client, budget):
        resp = auth_client.get("/api/v1/budgets")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None
        assert data.get("status") == "success"

    def test_create_budget(self, auth_client, category):
        resp = auth_client.post(
            "/api/v1/budgets",
            json={
                "category_id": category.id,
                "amount": 300.0,
                "period": "monthly",
                "start_date": date.today().replace(day=1).isoformat(),
            },
        )
        assert resp.status_code in (200, 201)


# ============================================================
# API v1 — Dashboard
# ============================================================


class TestAPIDashboard:
    """Tests fonctionnels pour /api/v1/dashboard"""

    def test_summary_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code in (302, 401)

    def test_summary_authenticated(self, auth_client, account, transaction):
        resp = auth_client.get("/api/v1/dashboard/summary")
        # 200 si OK, 500 si DashboardService a un souci interne
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None


# ============================================================
# API v1 — Auth
# ============================================================


class TestAPIAuth:
    """Tests fonctionnels pour /api/v1/auth"""

    def test_login_success(self, client, user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "TestPassword123!"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data is not None

    def test_login_invalid(self, client, user):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    def test_register(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "NewPassword123!",
            },
        )
        assert resp.status_code in (200, 201)
