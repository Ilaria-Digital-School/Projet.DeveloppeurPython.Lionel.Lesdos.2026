"""Tests de sécurité de l'authentification : 2FA (web et API), verrouillage, JWT."""

import pytest

from core.extensions import db

pytestmark = pytest.mark.integration

MOT_DE_PASSE = "TestPassword123!"  # cf. fixture user (conftest)
CODE = "123456"


@pytest.fixture(autouse=True)
def _sans_rate_limit(monkeypatch):
    # Les connexions sont limitées à 5/min : ces tests en font davantage
    from api.v1.auth import auth_limiter

    monkeypatch.setattr(auth_limiter, "enabled", False)


@pytest.fixture
def emails_2fa(monkeypatch):
    """Code 2FA e-mail déterministe ; mémorise les envois au lieu d'envoyer."""
    from core.security.email_2fa import EmailTwoFactorAuth

    envoyes = []
    monkeypatch.setattr(
        EmailTwoFactorAuth, "generate_email_code", staticmethod(lambda length=6: CODE)
    )
    monkeypatch.setattr(
        EmailTwoFactorAuth,
        "send_2fa_email",
        staticmethod(lambda email, code: envoyes.append((email, code)) or True),
    )
    return envoyes


@pytest.fixture
def user_2fa(user, db_session, emails_2fa):
    """Utilisateur avec 2FA par e-mail activée."""
    user.two_factor_enabled = True
    user.two_factor_secret = None
    db_session.commit()
    return user


def _recharger(user):
    db.session.expire_all()
    return user


def _api_login(client, email="test@example.com", password=MOT_DE_PASSE):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


def _web_login(client, password=MOT_DE_PASSE):
    return client.post(
        "/auth/login", data={"email": "test@example.com", "password": password}
    )


class TestConnexionApi:
    def test_sans_2fa_renvoie_des_jetons(self, client, user, db_session):
        db_session.commit()
        resp = _api_login(client)
        assert resp.status_code == 200
        assert resp.get_json()["access_token"]

    def test_mauvais_mot_de_passe(self, client, user, db_session):
        db_session.commit()
        assert _api_login(client, password="faux").status_code == 401

    def test_avec_2fa_ne_renvoie_aucun_jeton(self, client, user_2fa, emails_2fa):
        resp = _api_login(client)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" not in data and "refresh_token" not in data
        assert data["two_factor_required"] is True
        assert data["two_factor_token"]
        assert emails_2fa == [("test@example.com", CODE)]

    def test_2fa_bon_code_donne_acces(self, client, user_2fa):
        jeton_2fa = _api_login(client).get_json()["two_factor_token"]
        resp = client.post(
            "/api/v1/auth/2fa/verify",
            json={"two_factor_token": jeton_2fa, "code": CODE},
        )
        assert resp.status_code == 200, resp.get_json()
        access = resp.get_json()["access_token"]
        comptes = client.get(
            "/api/v1/comptes", headers={"Authorization": f"Bearer {access}"}
        )
        assert comptes.status_code == 200

    def test_2fa_mauvais_code_refuse(self, client, user_2fa):
        jeton_2fa = _api_login(client).get_json()["two_factor_token"]
        resp = client.post(
            "/api/v1/auth/2fa/verify",
            json={"two_factor_token": jeton_2fa, "code": "000000"},
        )
        assert resp.status_code == 401
        assert "access_token" not in resp.get_json()

    def test_2fa_jeton_invalide_refuse(self, client, user_2fa):
        resp = client.post(
            "/api/v1/auth/2fa/verify", json={"two_factor_token": "forge", "code": CODE}
        )
        assert resp.status_code == 401

    def test_2fa_echecs_verrouillent_le_compte(self, client, user_2fa):
        jeton_2fa = _api_login(client).get_json()["two_factor_token"]
        for _ in range(5):
            client.post(
                "/api/v1/auth/2fa/verify",
                json={"two_factor_token": jeton_2fa, "code": "000000"},
            )
        assert _recharger(user_2fa).is_locked is True
        # Même le bon code est refusé une fois le compte verrouillé
        resp = client.post(
            "/api/v1/auth/2fa/verify",
            json={"two_factor_token": jeton_2fa, "code": CODE},
        )
        assert resp.status_code in (401, 429)
        assert _api_login(client).status_code == 429

    def test_jeton_revoque_apres_deconnexion(self, client, user, db_session):
        db_session.commit()
        access = _api_login(client).get_json()["access_token"]
        entete = {"Authorization": f"Bearer {access}"}
        assert client.post("/api/v1/auth/logout", headers=entete).status_code == 200
        assert client.get("/api/v1/comptes", headers=entete).status_code == 401

    def test_compte_desactive_jeton_refuse(self, client, user, db_session):
        db_session.commit()
        access = _api_login(client).get_json()["access_token"]
        user.is_active = False
        db_session.commit()
        resp = client.get(
            "/api/v1/comptes", headers={"Authorization": f"Bearer {access}"}
        )
        assert resp.status_code == 401


class TestConnexionWeb2fa:
    def test_mot_de_passe_ne_connecte_pas_avant_la_2fa(self, client, user_2fa):
        resp = _web_login(client)
        assert resp.status_code == 302 and "/verify-2fa" in resp.headers["Location"]
        # Pas encore connecté
        assert client.get("/api/v1/comptes").status_code in (302, 401)

    def test_bon_code_connecte(self, client, user_2fa):
        _web_login(client)
        resp = client.post("/auth/verify-2fa", data={"code": CODE})
        assert resp.status_code == 302
        assert client.get("/api/v1/comptes").status_code == 200

    def test_echecs_2fa_verrouillent_le_compte(self, client, user_2fa):
        _web_login(client)
        for _ in range(5):
            client.post("/auth/verify-2fa", data={"code": "000000"})
        assert _recharger(user_2fa).is_locked is True
        client.post("/auth/verify-2fa", data={"code": CODE})
        assert client.get("/api/v1/comptes").status_code in (302, 401)

    def test_mot_de_passe_correct_ne_remet_pas_les_echecs_a_zero(
        self, client, user_2fa
    ):
        """4 mauvais mots de passe, puis le bon : le compteur reste à 4 tant que
        la 2FA n'est pas validée (sinon la 2FA ne compterait jamais)."""
        for _ in range(4):
            _web_login(client, password="faux")
        _web_login(client)
        assert _recharger(user_2fa).login_attempts == 4
        client.post("/auth/verify-2fa", data={"code": "000000"})
        assert _recharger(user_2fa).is_locked is True

    def test_succes_2fa_remet_les_echecs_a_zero(self, client, user_2fa):
        _web_login(client, password="faux")
        _web_login(client)
        client.post("/auth/verify-2fa", data={"code": CODE})
        assert _recharger(user_2fa).login_attempts == 0
