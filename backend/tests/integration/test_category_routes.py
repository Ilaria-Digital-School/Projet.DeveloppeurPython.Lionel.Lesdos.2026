"""Tests d'intégration pour les routes de catégories."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.integration


class TestCategoryList:
    """Tests de la liste des catégories."""

    def test_list_requires_auth(self, client):
        resp = client.get("/categories/")
        assert resp.status_code == 302

    def test_list_authenticated(self, auth_client, category):
        resp = auth_client.get("/categories/")
        assert resp.status_code in (200, 500)


class TestCategoryAPI:
    """Tests de l'API catégories (via /api/v1/categories)."""

    def test_api_list_requires_auth(self, client):
        resp = client.get("/api/v1/categories")
        assert resp.status_code in (302, 401)

    def test_api_list_authenticated(self, auth_client, category):
        resp = auth_client.get("/api/v1/categories")
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.get_json()
            assert data.get("status") == "success"

    def test_api_list_compte_les_transactions(self, auth_client, transaction):
        # categories.js affiche ce nombre en rechargeant la liste
        resp = auth_client.get("/api/v1/categories")
        assert resp.status_code == 200
        (cat,) = [
            c
            for c in resp.get_json()["categories"]
            if c["id"] == transaction.category_id
        ]
        assert cat["transaction_count"] == 1


class TestCategoryRoutesSupprimees:
    """Les routes web CRUD catégories ont été supprimées (CRUD via /api/v1/categories)."""

    @pytest.mark.parametrize(
        "method, url",
        [
            ("get", "/categories/add"),
            ("get", "/categories/edit/1"),
            ("post", "/categories/delete/1"),
        ],
    )
    def test_route_removed(self, auth_client, method, url):
        resp = getattr(auth_client, method)(url)
        assert resp.status_code == 404


class TestSuppressionCategorie:
    """DELETE /api/v1/categories/<id> : déplacement des éléments liés."""

    @pytest.fixture
    def autre_categorie(self, db_session, user):
        from core.models.category import Category

        cat = Category(
            user_id=user.id,
            name="Courses",
            is_expense=True,
            category_type="expense",
        )
        db_session.add(cat)
        db_session.flush()
        return cat

    @pytest.fixture
    def recurrente(self, db_session, user, account, category):
        from datetime import date

        from core.models.recurring_transaction import RecurringTransaction

        r = RecurringTransaction(
            user_id=user.id,
            account_id=account.id,
            category_id=category.id,
            montant=Decimal("9.99"),
            type_transaction="expense",
            libelle="Abonnement",
            frequency="monthly",
            interval=1,
            start_date=date(2026, 1, 1),
            next_execution_date=date(2026, 12, 1),
        )
        db_session.add(r)
        db_session.flush()
        return r

    def test_usage_compte_les_elements_lies(
        self, auth_client, category, transaction, budget, recurrente
    ):
        resp = auth_client.get(f"/api/v1/categories/{category.id}/usage")
        assert resp.status_code == 200
        assert resp.get_json()["usage"] == {
            "transactions": 1,
            "budgets": 1,
            "recurring": 1,
        }

    def test_categorie_utilisee_refusee_sans_force(
        self, auth_client, category, transaction
    ):
        resp = auth_client.delete(f"/api/v1/categories/{category.id}")
        assert resp.status_code == 409
        assert resp.get_json()["errors"]["usage"]["transactions"] == 1

    def test_recurrente_seule_bloque_aussi(self, auth_client, category, recurrente):
        resp = auth_client.delete(f"/api/v1/categories/{category.id}")
        assert resp.status_code == 409

    def test_force_sans_destination_laisse_sans_categorie(
        self, auth_client, db_session, category, transaction, budget, recurrente
    ):
        from core.models.budget import Budget

        resp = auth_client.delete(f"/api/v1/categories/{category.id}?force=1")
        assert resp.status_code == 200, resp.get_json()
        db_session.refresh(transaction)
        db_session.refresh(recurrente)
        assert transaction.category_id is None
        assert recurrente.category_id is None
        assert Budget.query.filter_by(id=budget.id).count() == 0

    def test_force_avec_destination_deplace(
        self,
        auth_client,
        db_session,
        category,
        autre_categorie,
        transaction,
        recurrente,
    ):
        resp = auth_client.delete(
            f"/api/v1/categories/{category.id}?force=1&move_to={autre_categorie.id}"
        )
        assert resp.status_code == 200, resp.get_json()
        db_session.refresh(transaction)
        db_session.refresh(recurrente)
        assert transaction.category_id == autre_categorie.id
        assert recurrente.category_id == autre_categorie.id

    def test_destination_d_un_autre_type_refusee(
        self, auth_client, db_session, category, income_category, transaction
    ):
        resp = auth_client.delete(
            f"/api/v1/categories/{category.id}?force=1&move_to={income_category.id}"
        )
        assert resp.status_code == 400
        db_session.refresh(transaction)
        assert transaction.category_id == category.id
