"""Tests de sécurité : réinitialisation et changement de mot de passe, inscription."""

import re
import time

import pytest

from core.extensions import db

pytestmark = pytest.mark.integration

ANCIEN = "TestPassword123!"  # cf. fixture user (conftest)
NOUVEAU = "NouveauMotDePasse456!"


@pytest.fixture(autouse=True)
def _sans_rate_limit(monkeypatch):
    from api.v1.auth import auth_limiter

    monkeypatch.setattr(auth_limiter, "enabled", False)


@pytest.fixture
def liens_reset(monkeypatch):
    """Capture les liens de réinitialisation au lieu d'envoyer l'e-mail."""
    import app.utils.email as email_utils

    liens = []
    monkeypatch.setattr(
        email_utils, "send_password_reset_email", lambda email, url: liens.append(url)
    )
    return liens


def _jeton(url):
    return url.rstrip("/").rsplit("/", 1)[-1]


def _demander_reset(client, email="test@example.com"):
    return client.post("/auth/reset-password-request", data={"email": email})


def _reset(client, jeton, mdp=NOUVEAU):
    return client.post(
        f"/auth/reset-password/{jeton}", data={"password": mdp, "password2": mdp}
    )


def _api_login(client, password):
    return client.post(
        "/api/v1/auth/login", json={"email": "test@example.com", "password": password}
    )


def _recharger(user):
    db.session.expire_all()
    return user


class TestDemandeDeReinitialisation:
    def test_meme_reponse_email_inconnu(self, client, user, db_session, liens_reset):
        db_session.commit()
        connu = _demander_reset(client).get_data(as_text=True)
        inconnu = _demander_reset(client, "personne@example.com").get_data(as_text=True)
        motif = re.compile(r"Un email de réinitialisation a été envoyé")
        assert motif.search(connu) and motif.search(inconnu)
        assert len(liens_reset) == 1

    def test_jeton_stocke_hache(self, client, user, db_session, liens_reset):
        db_session.commit()
        _demander_reset(client)
        jeton = _jeton(liens_reset[0])
        assert _recharger(user).reset_token and jeton not in user.reset_token


class TestReinitialisation:
    def test_jeton_valide_change_le_mot_de_passe(
        self, client, user, db_session, liens_reset
    ):
        db_session.commit()
        _demander_reset(client)
        resp = _reset(client, _jeton(liens_reset[0]))
        assert resp.status_code == 302
        assert _recharger(user).check_password(NOUVEAU)

    def test_jeton_a_usage_unique(self, client, user, db_session, liens_reset):
        db_session.commit()
        _demander_reset(client)
        jeton = _jeton(liens_reset[0])
        _reset(client, jeton)
        _reset(client, jeton, "EncoreUnAutre789!")
        assert _recharger(user).check_password(NOUVEAU)

    def test_jeton_expire(self, client, user, db_session, liens_reset):
        from datetime import datetime, timedelta, timezone

        db_session.commit()
        _demander_reset(client)
        user.reset_token_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()
        _reset(client, _jeton(liens_reset[0]))
        assert _recharger(user).check_password(ANCIEN)

    def test_mot_de_passe_faible_refuse(self, client, user, db_session, liens_reset):
        db_session.commit()
        _demander_reset(client)
        _reset(client, _jeton(liens_reset[0]), "faible")
        assert _recharger(user).check_password(ANCIEN)

    def test_deverrouille_le_compte(self, client, user, db_session, liens_reset):
        user.is_locked = True
        user.login_attempts = 5
        db_session.commit()
        _demander_reset(client)
        _reset(client, _jeton(liens_reset[0]))
        assert _recharger(user).is_locked is False
        assert user.login_attempts == 0


class TestInvalidationDesAccesExistants:
    """Changer de mot de passe coupe les sessions et jetons ouverts avant."""

    def test_jeton_jwt_refuse_apres_reinitialisation(
        self, client, user, db_session, liens_reset
    ):
        db_session.commit()
        access = _api_login(client, ANCIEN).get_json()["access_token"]
        entete = {"Authorization": f"Bearer {access}"}
        assert client.get("/api/v1/comptes", headers=entete).status_code == 200
        time.sleep(1.1)  # iat est à la seconde près
        _demander_reset(client)
        _reset(client, _jeton(liens_reset[0]))
        assert client.get("/api/v1/comptes", headers=entete).status_code == 401
        # Une nouvelle connexion fonctionne
        nouveau = _api_login(client, NOUVEAU).get_json()["access_token"]
        assert (
            client.get(
                "/api/v1/comptes", headers={"Authorization": f"Bearer {nouveau}"}
            ).status_code
            == 200
        )

    def test_session_web_coupee_apres_reinitialisation(
        self, app, client, user, db_session, liens_reset
    ):
        db_session.commit()
        client.post(
            "/auth/login", data={"email": "test@example.com", "password": ANCIEN}
        )
        assert client.get("/api/v1/comptes").status_code == 200
        time.sleep(1.1)
        # Réinitialisation faite ailleurs (autre navigateur, non connecté)
        from flask import g

        autre = app.test_client()
        g.pop("_login_user", None)  # cf. fixture client (conftest)
        autre.post("/auth/reset-password-request", data={"email": "test@example.com"})
        g.pop("_login_user", None)
        _reset(autre, _jeton(liens_reset[0]))
        assert client.get("/api/v1/comptes").status_code in (302, 401)

    def test_changement_depuis_le_profil_garde_la_session_courante(
        self, client, user, db_session
    ):
        db_session.commit()
        client.post(
            "/auth/login", data={"email": "test@example.com", "password": ANCIEN}
        )
        time.sleep(1.1)
        client.post(
            "/profile/change-password",
            data={
                "current_password": ANCIEN,
                "new_password": NOUVEAU,
                "confirm_password": NOUVEAU,
            },
        )
        assert _recharger(user).check_password(NOUVEAU)
        assert client.get("/api/v1/comptes").status_code == 200

    def test_changement_profil_mot_de_passe_faible_refuse(
        self, client, user, db_session
    ):
        db_session.commit()
        client.post(
            "/auth/login", data={"email": "test@example.com", "password": ANCIEN}
        )
        client.post(
            "/profile/change-password",
            data={
                "current_password": ANCIEN,
                "new_password": "toutenminuscules",
                "confirm_password": "toutenminuscules",
            },
        )
        assert _recharger(user).check_password(ANCIEN)


class TestReinitialisationParAdmin:
    def test_mot_de_passe_temporaire_aleatoire_et_jetons_coupes(
        self, app, admin_client, user, admin_user, db_session
    ):
        from flask import g

        db_session.commit()
        # admin_client partage le client (et la session admin) : jeton de
        # l'utilisateur obtenu et vérifié depuis un client sans session
        sans_session = app.test_client()
        g.pop("_login_user", None)
        access = _api_login(sans_session, ANCIEN).get_json()["access_token"]
        time.sleep(1.1)
        g.pop("_login_user", None)
        resp = admin_client.post(f"/api/v1/admin/users/{user.id}/reset-password")
        assert resp.status_code == 200, resp.get_json()
        assert not _recharger(user).check_password(ANCIEN)
        g.pop("_login_user", None)
        entete = {"Authorization": f"Bearer {access}"}
        assert sans_session.get("/api/v1/comptes", headers=entete).status_code == 401


class TestInscription:
    def test_api_mot_de_passe_faible_refuse(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "n@example.com",
                "username": "nouveau",
                "password": "faible",
            },
        )
        assert resp.status_code == 400

    def test_api_inscription_valide(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "n@example.com", "username": "nouveau", "password": NOUVEAU},
        )
        assert resp.status_code == 201, resp.get_json()

    def test_api_email_deja_utilise(self, client, user, db_session):
        db_session.commit()
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "autre",
                "password": NOUVEAU,
            },
        )
        assert resp.status_code in (400, 409)
