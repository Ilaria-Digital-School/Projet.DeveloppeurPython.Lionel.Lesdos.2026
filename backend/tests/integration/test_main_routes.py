"""Tests d'intégration pour les routes principales."""

import pytest

pytestmark = pytest.mark.integration


class TestIndexRoute:
    """Tests de la route racine GET /."""

    def test_index_returns_200_or_redirect(self, client):
        resp = client.get("/")
        assert resp.status_code in (200, 302, 500)

    def test_index_authenticated(self, auth_client):
        resp = auth_client.get("/")
        assert resp.status_code in (200, 302, 500)


class TestStatusRoute:
    """Tests de la route GET /status."""

    def test_status_returns_json(self, client):
        resp = client.get("/status")
        assert resp.status_code in (200, 302, 500)


class TestInfoRoute:
    """Tests de la route GET /info."""

    def test_info_returns_json(self, client):
        resp = client.get("/info")
        assert resp.status_code in (200, 302, 500)


class TestNotFoundRoute:
    """Tests du gestionnaire 404."""

    def test_404_web_returns_html(self, client):
        resp = client.get("/nonexistent-route-xyz")
        assert resp.status_code == 404
        assert b"error-container" in resp.data

    def test_404_api_returns_json(self, client):
        resp = client.get("/api/v1/nonexistent-route-xyz")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data


class TestHealthz:
    def test_repond_sans_connexion(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.get_json() == {"status": "ok"}

    def test_base_injoignable(self, client, monkeypatch):
        from core.extensions import db

        vrai_execute = db.session.execute

        def panne(requete, *args, **kwargs):
            # Seule la sonde échoue : le nettoyage de la base (fixture) passe
            if str(requete) == "SELECT 1":
                raise RuntimeError("connexion refusée")
            return vrai_execute(requete, *args, **kwargs)

        monkeypatch.setattr(db.session, "execute", panne)
        resp = client.get("/healthz")
        assert resp.status_code == 503
        assert resp.get_json() == {"status": "error"}  # aucun détail exposé

    def test_exempte_de_la_limite_de_requetes(self, client):
        # Au-delà de la limite horaire par défaut (500/h, compteur partagé par
        # tous les visiteurs non connectés) : la sonde Docker, à 120 appels
        # par heure, passait en 429 et le conteneur en "unhealthy"
        codes = {client.get("/healthz").status_code for _ in range(501)}
        assert codes == {200}
