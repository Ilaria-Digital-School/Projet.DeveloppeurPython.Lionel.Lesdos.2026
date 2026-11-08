"""Tests de l'export des données et de la suppression de compte (/api/v1/settings)."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from core.extensions import db

pytestmark = pytest.mark.integration

MOT_DE_PASSE = "TestPassword123!"  # cf. fixture user (conftest)


@pytest.fixture(autouse=True)
def _sans_rate_limit(monkeypatch):
    from api.v1.auth import auth_limiter

    monkeypatch.setattr(auth_limiter, "enabled", False)


@pytest.fixture
def donnees(db_session, user, account, category):
    """Une transaction, un budget et une récurrence pour l'utilisateur."""
    from datetime import date

    from core.models.budget import Budget
    from core.models.recurring_transaction import RecurringTransaction
    from core.models.transactions import Transaction

    db_session.add_all(
        [
            Transaction(
                user_id=user.id,
                account_id=account.id,
                category_id=category.id,
                montant=Decimal("42.00"),
                type_transaction="achat",
                libelle="Courses",
                date_heure_transaction=datetime(2026, 6, 1, 12),
                statut="completed",
                devise="EUR",
            ),
            Budget(
                user_id=user.id,
                category_id=category.id,
                amount=Decimal("300"),
                period="monthly",
                start_date=date.today().replace(day=1),
            ),
            RecurringTransaction(
                user_id=user.id,
                account_id=account.id,
                montant=Decimal("10"),
                type_transaction="abonnement",
                libelle="Musique",
                frequency="monthly",
                interval=1,
                start_date=date.today(),
                next_execution_date=date.today(),
            ),
        ]
    )
    db_session.commit()


def _supprimer(client, password=MOT_DE_PASSE):
    return client.delete("/api/v1/settings/account", json={"password": password})


def _connexion_web(client):
    return client.post(
        "/auth/login", data={"email": "test@example.com", "password": MOT_DE_PASSE}
    )


def _compter(table, user_id, colonne="user_id"):
    return db.session.execute(
        db.text(f"SELECT count(*) FROM {table} WHERE {colonne} = :u"), {"u": user_id}
    ).scalar()


class TestExport:
    def test_export_contient_mes_donnees_sans_secret(self, auth_client, user, donnees):
        resp = auth_client.get("/api/v1/settings/export")
        assert resp.status_code == 200, resp.get_data(as_text=True)[:300]
        assert "attachment" in resp.headers["Content-Disposition"]
        contenu = json.loads(resp.get_data(as_text=True))
        assert contenu["user"]["email"] == "test@example.com"
        assert [t["description"] for t in contenu["transactions"]] == ["Courses"]
        brut = resp.get_data(as_text=True)
        for secret in ("password_hash", "pbkdf2", "two_factor_secret", "reset_token"):
            assert secret not in brut

    def test_export_n_inclut_pas_les_donnees_des_autres(
        self, auth_client, user, donnees, admin_user, db_session
    ):
        from core.models.account import Account

        db_session.add(
            Account(user_id=admin_user.id, name="Compte admin", balance=Decimal("9"))
        )
        db_session.commit()
        contenu = json.loads(
            auth_client.get("/api/v1/settings/export").get_data(as_text=True)
        )
        assert "Compte admin" not in json.dumps(contenu)

    def test_export_requiert_connexion(self, client):
        assert client.get("/api/v1/settings/export").status_code in (302, 401)


class TestDemandeDeSuppression:
    def test_mauvais_mot_de_passe_refuse(self, auth_client, user):
        assert _supprimer(auth_client, "faux").status_code == 403
        db.session.expire_all()
        assert user.is_active is True and user.deletion_scheduled_at is None

    def test_suppression_planifiee_et_deconnexion(self, auth_client, user):
        assert _supprimer(auth_client).status_code == 200
        db.session.expire_all()
        assert user.is_active is False
        delai = user.deletion_scheduled_at.replace(tzinfo=timezone.utc) - datetime.now(
            timezone.utc
        )
        assert timedelta(days=6, hours=23) < delai <= timedelta(days=7)
        assert auth_client.get("/api/v1/comptes").status_code in (302, 401)

    def test_jeton_api_refuse_apres_demande(self, client, user, db_session):
        db_session.commit()
        access = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": MOT_DE_PASSE},
        ).get_json()["access_token"]
        entete = {"Authorization": f"Bearer {access}"}
        assert (
            client.delete(
                "/api/v1/settings/account",
                json={"password": MOT_DE_PASSE},
                headers=entete,
            ).status_code
            == 200
        )
        assert client.get("/api/v1/comptes", headers=entete).status_code == 401


class TestAnnulation:
    def test_se_reconnecter_annule_la_suppression(self, auth_client, user):
        _supprimer(auth_client)
        resp = _connexion_web(auth_client)
        assert resp.status_code == 302 and "/auth/login" not in resp.headers["Location"]
        db.session.expire_all()
        assert user.is_active is True and user.deletion_scheduled_at is None
        assert auth_client.get("/api/v1/comptes").status_code == 200

    def test_compte_desactive_par_un_admin_reste_bloque(self, client, user, db_session):
        user.is_active = False
        db_session.commit()
        _connexion_web(client)
        db.session.expire_all()
        assert user.is_active is False
        assert client.get("/api/v1/comptes").status_code in (302, 401)

    def test_apres_le_delai_plus_d_annulation(self, auth_client, user, db_session):
        _supprimer(auth_client)
        user.deletion_scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()
        _connexion_web(auth_client)
        db.session.expire_all()
        assert user.is_active is False


class TestPurge:
    def test_purge_supprime_toutes_les_donnees(
        self, auth_client, user, donnees, db_session
    ):
        from core.services.user.account_deletion import purger_comptes_a_supprimer

        user_id = user.id
        _supprimer(auth_client)
        user.deletion_scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()
        assert purger_comptes_a_supprimer() == 1
        for table in (
            "transactions",
            "budgets",
            "recurring_transactions",
            "categories",
        ):
            assert _compter(table, user_id) == 0, table
        assert _compter('"ComptesBancaires"', user_id, "utilisateur_id") == 0
        assert _compter("users", user_id, "id") == 0

    def test_purge_epargne_les_comptes_dans_le_delai(self, auth_client, user, donnees):
        from core.services.user.account_deletion import purger_comptes_a_supprimer

        _supprimer(auth_client)
        assert purger_comptes_a_supprimer() == 0
        assert _compter("users", user.id, "id") == 1

    def test_purge_epargne_les_comptes_desactives_par_un_admin(self, user, db_session):
        from core.services.user.account_deletion import purger_comptes_a_supprimer

        user.is_active = False
        user.deactivated_at = datetime.now(timezone.utc) - timedelta(days=30)
        db_session.commit()
        assert purger_comptes_a_supprimer() == 0
        assert _compter("users", user.id, "id") == 1

    def test_commande_cli(self, app, auth_client, user, db_session):
        _supprimer(auth_client)
        user.deletion_scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()
        res = app.test_cli_runner().invoke(args=["accounts", "purge-deleted"])
        assert res.exit_code == 0, res.output
        assert "1 compte(s) supprimé(s)" in res.output


class TestDesactivation2fa:
    @pytest.fixture
    def user_2fa(self, user, db_session):
        user.two_factor_enabled = True
        db_session.commit()
        return user

    def _alertes(self, user):
        from core.models.notification import Notification

        db.session.expire_all()
        return Notification.query.filter_by(
            user_id=user.id, notification_type="security_alert"
        ).all()

    @pytest.mark.parametrize(
        "url", ["/api/v1/profil/2fa/disable", "/api/v1/profil/email-2fa/disable"]
    )
    def test_mauvais_mot_de_passe_refuse(self, auth_client, user_2fa, url):
        assert auth_client.post(url, json={"password": "faux"}).status_code == 401
        db.session.expire_all()
        assert user_2fa.two_factor_enabled is True
        assert self._alertes(user_2fa) == []

    @pytest.mark.parametrize(
        "url", ["/api/v1/profil/2fa/disable", "/api/v1/profil/email-2fa/disable"]
    )
    def test_desactivation_envoie_une_alerte(self, auth_client, user_2fa, url):
        assert auth_client.post(url, json={"password": MOT_DE_PASSE}).status_code == 200
        db.session.expire_all()
        assert user_2fa.two_factor_enabled is False
        (alerte,) = self._alertes(user_2fa)
        assert "désactivée" in alerte.message


class TestPurgePhoto:
    def test_photo_supprimee_a_la_purge(
        self, app, auth_client, user, db_session, tmp_path, monkeypatch
    ):
        from core.services.user.account_deletion import purger_comptes_a_supprimer

        monkeypatch.setattr(app, "static_folder", str(tmp_path))
        dossier = tmp_path / "uploads" / "avatars"
        dossier.mkdir(parents=True)
        photo = dossier / f"user_{user.id}.png"
        autre = dossier / f"user_{user.id + 1000}.png"
        photo.write_bytes(b"x")
        autre.write_bytes(b"x")
        _supprimer(auth_client)
        user.deletion_scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()
        purger_comptes_a_supprimer()
        assert not photo.exists()
        assert autre.exists()
