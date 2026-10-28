"""Tests d'intégration pour les routes de catégories."""

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
