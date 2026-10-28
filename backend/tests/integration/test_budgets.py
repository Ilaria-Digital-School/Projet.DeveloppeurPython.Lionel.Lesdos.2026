"""Tests des budgets : montant dépensé sur la période en cours et alertes."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta

from core.extensions import db

pytestmark = pytest.mark.integration

AUJOURD_HUI = date.today()
DEBUT_MOIS = AUJOURD_HUI.replace(day=1)


@pytest.fixture
def nouveau_budget(db_session, user, category):
    from core.models.budget import Budget

    def fabriquer(montant="500.00", period="monthly", start_date=None, **kw):
        b = Budget(
            user_id=user.id,
            category_id=category.id,
            amount=Decimal(montant),
            period=period,
            start_date=start_date or DEBUT_MOIS,
            **kw,
        )
        db_session.add(b)
        db_session.commit()
        return b

    return fabriquer


@pytest.fixture
def depense(db_session, user, account, category):
    from core.models.transactions import Transaction

    def fabriquer(montant, quand, category_id=category.id):
        t = Transaction(
            user_id=user.id,
            account_id=account.id,
            category_id=category_id,
            montant=Decimal(montant),
            type_transaction="achat",
            libelle="Dépense",
            date_heure_transaction=quand,
            statut="completed",
            devise="EUR",
        )
        db_session.add(t)
        db_session.commit()
        return t

    return fabriquer


def _midi(jour):
    return datetime.combine(jour, datetime.min.time()).replace(hour=12)


def _alertes(user):
    from core.models.notification import Notification

    db.session.expire_all()
    return (
        Notification.query.filter_by(user_id=user.id, notification_type="budget_alert")
        .order_by(Notification.id)
        .all()
    )


class TestMontantDepense:
    def test_mensuel_compte_seulement_le_mois_en_cours(self, nouveau_budget, depense):
        b = nouveau_budget(start_date=DEBUT_MOIS - relativedelta(months=3))
        depense("400.00", _midi(DEBUT_MOIS - relativedelta(months=2)))
        depense("50.00", _midi(DEBUT_MOIS))
        assert b.get_used_amount() == 50.0

    def test_depense_du_jour_comptee(self, nouveau_budget, depense):
        b = nouveau_budget()
        depense(
            "30.00", datetime.combine(AUJOURD_HUI, datetime.min.time()).replace(hour=18)
        )
        assert b.get_used_amount() == 30.0

    def test_annuel_compte_l_annee_en_cours(self, nouveau_budget, depense):
        b = nouveau_budget(period="yearly", start_date=date(AUJOURD_HUI.year - 1, 1, 1))
        depense("100.00", _midi(date(AUJOURD_HUI.year - 1, 6, 1)))
        depense("70.00", _midi(date(AUJOURD_HUI.year, 1, 1)))
        assert b.get_used_amount() == 70.0

    def test_autre_categorie_ignoree(self, nouveau_budget, depense, db_session, user):
        from core.models.category import Category

        autre = Category(user_id=user.id, name="Autre", category_type="expense")
        db_session.add(autre)
        db_session.commit()
        b = nouveau_budget()
        depense("90.00", _midi(DEBUT_MOIS), category_id=autre.id)
        assert b.get_used_amount() == 0.0


class TestApiBudgets:
    def test_liste_et_resume_utilisent_le_mois_en_cours(
        self, auth_client, nouveau_budget, depense
    ):
        nouveau_budget(
            montant="200.00", start_date=DEBUT_MOIS - relativedelta(months=5)
        )
        depense("150.00", _midi(DEBUT_MOIS - relativedelta(months=1)))
        depense("50.00", _midi(DEBUT_MOIS))

        (b,) = auth_client.get("/api/v1/budgets").get_json()["budgets"]
        assert b["spent_amount"] == 50.0
        assert b["spent_percentage"] == 25.0

        resume = auth_client.get("/api/v1/budgets/summary").get_json()
        (b,) = resume["budgets"]
        fin_mois = DEBUT_MOIS + relativedelta(months=1) - timedelta(days=1)
        assert b["days_total"] == (fin_mois - DEBUT_MOIS).days
        assert resume["summary"]["total_spent"] == 50.0

    def test_crud(self, auth_client, category):
        resp = auth_client.post(
            "/api/v1/budgets", json={"category_id": category.id, "amount": 300}
        )
        assert resp.status_code in (200, 201), resp.get_json()
        bid = resp.get_json()["budget"]["id"]
        assert auth_client.get(f"/api/v1/budgets/{bid}").status_code == 200
        resp = auth_client.put(
            f"/api/v1/budgets/{bid}", json={"category_id": category.id, "amount": 450}
        )
        assert resp.status_code == 200, resp.get_json()
        assert auth_client.delete(f"/api/v1/budgets/{bid}").status_code == 200
        assert auth_client.get(f"/api/v1/budgets/{bid}").status_code == 404

        # L'historique survit à la suppression (budget_id remis à NULL)
        from core.models.budget_history import BudgetHistory

        db.session.expire_all()
        actions = {h.action for h in BudgetHistory.query.filter_by(budget_id=None)}
        assert "delete" in actions

    def test_montant_invalide_refuse(self, auth_client, category):
        resp = auth_client.post(
            "/api/v1/budgets", json={"category_id": category.id, "amount": -5}
        )
        assert resp.status_code == 400

    def test_budget_d_un_autre_utilisateur_inaccessible(
        self, auth_client, admin_user, db_session
    ):
        from core.models.budget import Budget
        from core.models.category import Category

        cat = Category(user_id=admin_user.id, name="X", category_type="expense")
        db_session.add(cat)
        db_session.flush()
        b = Budget(
            user_id=admin_user.id,
            category_id=cat.id,
            amount=Decimal("10"),
            period="monthly",
            start_date=DEBUT_MOIS,
        )
        db_session.add(b)
        db_session.commit()
        assert auth_client.get(f"/api/v1/budgets/{b.id}").status_code == 404
        assert auth_client.delete(f"/api/v1/budgets/{b.id}").status_code == 404


class TestAlertes:
    def test_seuil_du_budget_respecte(self, user, nouveau_budget, depense):
        from core.services.budgets.budget_services import check_budget_notifications

        nouveau_budget(montant="100.00", notification_threshold=50)
        depense("60.00", _midi(DEBUT_MOIS))
        check_budget_notifications(user.id)
        (alerte,) = _alertes(user)
        assert "60" in alerte.message

    def test_alerte_seuil_puis_depassement(self, user, nouveau_budget, depense):
        from core.services.budgets.budget_services import check_budget_notifications

        nouveau_budget(montant="100.00", notification_threshold=80)
        depense("85.00", _midi(DEBUT_MOIS))
        check_budget_notifications(user.id)
        assert len(_alertes(user)) == 1

        depense("30.00", _midi(DEBUT_MOIS))  # 115 %
        check_budget_notifications(user.id)
        alertes = _alertes(user)
        assert len(alertes) == 2
        assert "dépassé" in alertes[1].message

    def test_pas_de_doublon_au_meme_niveau(self, user, nouveau_budget, depense):
        from core.services.budgets.budget_services import check_budget_notifications

        nouveau_budget(montant="100.00", notification_threshold=80)
        depense("85.00", _midi(DEBUT_MOIS))
        check_budget_notifications(user.id)
        check_budget_notifications(user.id)
        depense("5.00", _midi(DEBUT_MOIS))
        check_budget_notifications(user.id)
        assert len(_alertes(user)) == 1

    def test_nouvelle_alerte_le_mois_suivant(self, user, nouveau_budget, depense):
        from core.services.budgets.budget_services import check_budget_notifications

        nouveau_budget(montant="100.00", notification_threshold=80)
        depense("85.00", _midi(DEBUT_MOIS))
        check_budget_notifications(user.id)

        mois_suivant = DEBUT_MOIS + relativedelta(months=1)
        depense("90.00", _midi(mois_suivant))
        check_budget_notifications(user.id, today=mois_suivant)
        assert len(_alertes(user)) == 2

    def test_sous_le_seuil_pas_d_alerte(self, user, nouveau_budget, depense):
        from core.services.budgets.budget_services import check_budget_notifications

        nouveau_budget(montant="100.00", notification_threshold=90)
        depense("75.00", _midi(DEBUT_MOIS))
        check_budget_notifications(user.id)
        assert _alertes(user) == []
