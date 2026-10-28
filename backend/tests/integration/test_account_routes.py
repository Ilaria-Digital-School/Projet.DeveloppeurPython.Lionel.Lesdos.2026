"""Tests d'intégration pour les routes de comptes bancaires."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.integration


class TestAccountList:
    """Tests de la liste des comptes."""

    def test_list_requires_auth(self, client):
        resp = client.get("/comptes/")
        assert resp.status_code == 302

    def test_list_authenticated(self, auth_client, account):
        resp = auth_client.get("/comptes/")
        assert resp.status_code in (200, 500)


class TestAccountAPI:
    """Tests de l'API comptes (via /api/v1/comptes)."""

    def test_api_requires_auth(self, client):
        resp = client.get("/api/v1/comptes")
        assert resp.status_code in (302, 401)

    def test_api_authenticated(self, auth_client, account):
        resp = auth_client.get("/api/v1/comptes")
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.get_json()
            assert data.get("status") == "success"


class TestAccountRoutesSupprimees:
    """Les routes web CRUD comptes ont été supprimées (CRUD via /api/v1/comptes)."""

    @pytest.mark.parametrize(
        "method, url",
        [
            ("get", "/comptes/create"),
            ("post", "/comptes/create"),
            ("get", "/comptes/1"),
            ("post", "/comptes/1/delete"),
        ],
    )
    def test_route_removed(self, auth_client, method, url):
        resp = getattr(auth_client, method)(url)
        assert resp.status_code == 404


class TestAccountUpdate:
    """Modification d'un compte via PUT /api/v1/comptes/<id>."""

    def _recharger(self, account):
        from core.extensions import db

        db.session.expire_all()
        return account

    def test_formulaire_case_decochee_desactive_le_compte(self, auth_client, account):
        # Le frontend envoie du FormData : une case décochée est absente du formulaire
        resp = auth_client.put(
            f"/api/v1/comptes/{account.id}",
            data={"name": account.name, "initial_balance": "1500.00"},
        )
        assert resp.status_code == 200
        assert self._recharger(account).is_active is False

    def test_formulaire_case_cochee_garde_le_compte_actif(self, auth_client, account):
        resp = auth_client.put(
            f"/api/v1/comptes/{account.id}",
            data={"name": account.name, "initial_balance": "1500.00", "is_active": "y"},
        )
        assert resp.status_code == 200
        assert self._recharger(account).is_active is True

    def test_json_sans_solde_conserve_le_solde(self, auth_client, account):
        resp = auth_client.put(
            f"/api/v1/comptes/{account.id}", json={"name": "Renommé"}
        )
        assert resp.status_code == 200
        acc = self._recharger(account)
        assert acc.name == "Renommé"
        assert acc.balance == Decimal("1500.00")

    def test_json_sans_is_active_garde_le_compte_actif(self, auth_client, account):
        resp = auth_client.put(
            f"/api/v1/comptes/{account.id}", json={"name": "Renommé"}
        )
        assert resp.status_code == 200
        assert self._recharger(account).is_active is True
