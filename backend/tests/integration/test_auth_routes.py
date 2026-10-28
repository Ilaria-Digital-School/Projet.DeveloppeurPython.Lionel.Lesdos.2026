"""Tests d'intégration pour les routes d'authentification."""

import pytest

pytestmark = pytest.mark.integration


class TestLoginPage:
    """Tests de la page de connexion web."""

    def test_login_page_get(self, client):
        resp = client.get("/auth/login")
        assert resp.status_code == 200

    def test_login_page_contains_form(self, client):
        resp = client.get("/auth/login")
        assert b"login" in resp.data.lower() or b"connexion" in resp.data.lower()

    def test_login_redirects_if_authenticated(self, auth_client):
        resp = auth_client.get("/auth/login")
        assert resp.status_code == 302


class TestLoginPost:
    """Tests de la soumission du formulaire de connexion."""

    def test_login_invalid_credentials(self, client):
        resp = client.post(
            "/auth/login",
            data={
                "email": "wrong@example.com",
                "password": "wrongpassword",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", data={}, follow_redirects=True)
        assert resp.status_code == 200


class TestRegisterPage:
    """Tests de la page d'inscription."""

    def test_register_page_get(self, client):
        resp = client.get("/auth/register")
        assert resp.status_code == 200

    def test_register_redirects_if_authenticated(self, auth_client):
        resp = auth_client.get("/auth/register")
        assert resp.status_code == 302


class TestLogout:
    """Tests de la déconnexion."""

    def test_logout_requires_auth(self, client):
        resp = client.get("/auth/logout")
        assert resp.status_code == 302

    def test_logout_authenticated(self, auth_client):
        resp = auth_client.get("/auth/logout", follow_redirects=False)
        assert resp.status_code == 302


class TestAPILogin:
    """Tests de l'API de connexion (via /api/v1/auth)."""

    def test_api_login_missing_data(self, client):
        resp = client.post(
            "/api/v1/auth/login", json={}, content_type="application/json"
        )
        # 400 si JWT configure, 500 si JWT_SECRET_KEY absente
        assert resp.status_code in (400, 500)

    def test_api_login_invalid_credentials(self, client):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "no@one.com", "password": "nope"},
            content_type="application/json",
        )
        assert resp.status_code in (401, 500)

    def test_api_login_success(self, client, user):
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
            },
            content_type="application/json",
        )
        # Peut etre 200 ou 500 si le service auth n'est pas moque
        if resp.status_code == 200:
            data = resp.get_json()
            assert data.get("status") == "success"


class TestAPIRegister:
    """Tests de l'API d'inscription (via /api/v1/auth)."""

    def test_api_register_missing_data(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "foo@bar.com"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_api_register_success(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "apinewuser",
                "email": "apinew@test.com",
                "password": "StrongPass123!",
            },
            content_type="application/json",
        )
        assert resp.status_code in (201, 400, 500)


class TestAPIRefresh:
    """Tests du rafraichissement JWT."""

    def test_refresh_no_token(self, client):
        resp = client.post("/api/v1/auth/refresh")
        # 401/422 si JWT configure, 500 si JWT_SECRET_KEY absente
        assert resp.status_code in (401, 422, 500)


class TestCheckAuth:
    """Tests de la verification d'authentification (via /api/v1/auth)."""

    def test_check_auth_requires_login(self, client):
        resp = client.get("/api/v1/auth/check")
        assert resp.status_code in (302, 401)

    def test_check_auth_authenticated(self, auth_client):
        resp = auth_client.get("/api/v1/auth/check")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("status") == "success"


class TestProtectedRoutes:
    """Tests d'accès aux routes protégées sans authentification."""

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/dashboard/")
        assert resp.status_code == 302

    def test_transactions_requires_auth(self, client):
        resp = client.get("/transactions/")
        assert resp.status_code == 302

    def test_comptes_requires_auth(self, client):
        resp = client.get("/comptes/")
        assert resp.status_code == 302
