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
        assert b["days_total"] == (fin_mois - DEBUT_MOIS).days + 1  # bornes incluses
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


# ── Indicateurs, report, historique ──────────────────────────────────────────

LE_10_MARS = date(2026, 3, 10)  # mars : 31 jours


class TestIndicateurs:
    def test_projection_et_reste_par_jour(self, nouveau_budget, depense):
        b = nouveau_budget(montant="310.00", start_date=date(2026, 1, 1))
        depense("100.00", _midi(date(2026, 3, 2)))
        i = b.indicateurs(LE_10_MARS)
        assert i["days_total"] == 31
        assert i["days_elapsed"] == 10
        assert i["days_remaining"] == 22  # le 10 compte encore
        assert i["projected_amount"] == 310.0  # 100 € / 10 j * 31 j
        assert i["remaining"] == 210.0
        assert i["daily_allowance"] == round(210 / 22, 2)
        assert i["velocity"] == "on_track"
        assert i["projection_method"] == "linear"  # aucun historique

    def test_depense_ponctuelle_non_extrapolee(self, nouveau_budget, depense):
        # Loyer payé le 1er : la projection ne doit pas faire 31 x 950 €
        b = nouveau_budget(montant="1000.00", start_date=date(2025, 12, 1))
        for mois in (12, 1, 2, 3):
            annee = 2025 if mois == 12 else 2026
            depense("950.00", _midi(date(annee, mois, 1)))
        i = b.indicateurs(LE_10_MARS)
        assert i["projection_method"] == "history"
        assert i["projected_amount"] == 950.0
        assert i["velocity"] == "on_track"

    def test_depense_future_deja_saisie_pas_comptee_deux_fois(
        self, nouveau_budget, depense
    ):
        # Loyer le 15 de chaque mois, celui de mars déjà saisi le 10
        b = nouveau_budget(montant="1000.00", start_date=date(2025, 12, 1))
        for annee, mois in ((2025, 12), (2026, 1), (2026, 2), (2026, 3)):
            depense("950.00", _midi(date(annee, mois, 15)))
        assert b.indicateurs(LE_10_MARS)["projected_amount"] == 950.0

    def test_projection_ajoute_le_reste_habituel(self, nouveau_budget, depense):
        b = nouveau_budget(montant="400.00", start_date=date(2026, 3, 1))
        # Les 3 mois précédents : 100 € avant le 10, 200 € après
        for annee, mois in ((2025, 12), (2026, 1), (2026, 2)):
            depense("100.00", _midi(date(annee, mois, 5)))
            depense("200.00", _midi(date(annee, mois, 20)))
        depense("150.00", _midi(date(2026, 3, 4)))
        i = b.indicateurs(LE_10_MARS)
        assert i["projected_amount"] == 350.0  # 150 dépensés + 200 habituels

    def test_depassement(self, nouveau_budget, depense):
        b = nouveau_budget(montant="100.00", start_date=date(2026, 1, 1))
        depense("150.00", _midi(date(2026, 3, 5)))
        i = b.indicateurs(LE_10_MARS)
        assert i["is_over_budget"] is True
        assert i["spent_percentage"] == 100.0
        assert i["raw_percentage"] == 150.0
        assert i["daily_allowance"] == 0.0
        assert i["velocity"] == "high"

    def test_budget_inactif(self, nouveau_budget):
        b = nouveau_budget(start_date=date(2026, 4, 1))
        i = b.indicateurs(LE_10_MARS)
        assert i["active"] is False
        assert i["days_total"] == 0


class TestReport:
    def test_reste_du_mois_precedent_reporte(self, nouveau_budget, depense):
        b = nouveau_budget(
            montant="300.00", start_date=date(2026, 1, 1), report_actif=True
        )
        depense("250.00", _midi(date(2026, 2, 14)))  # reste 50 € en février
        depense("100.00", _midi(date(2026, 3, 3)))
        assert b.montant_report(LE_10_MARS) == 50.0
        i = b.indicateurs(LE_10_MARS)
        assert i["available_amount"] == 350.0
        assert i["remaining"] == 250.0

    def test_depassement_non_reporte(self, nouveau_budget, depense):
        b = nouveau_budget(
            montant="300.00", start_date=date(2026, 1, 1), report_actif=True
        )
        depense("400.00", _midi(date(2026, 2, 14)))
        assert b.montant_report(LE_10_MARS) == 0.0

    def test_rien_avant_la_creation(self, nouveau_budget, depense):
        b = nouveau_budget(
            montant="300.00", start_date=date(2026, 3, 1), report_actif=True
        )
        assert b.montant_report(LE_10_MARS) == 0.0

    def test_report_desactive(self, nouveau_budget):
        b = nouveau_budget(montant="300.00", start_date=date(2026, 1, 1))
        assert b.montant_report(LE_10_MARS) == 0.0
        assert b.montant_disponible(LE_10_MARS) == 300.0

    def test_alerte_tient_compte_du_report(self, user, nouveau_budget, depense):
        from core.services.budgets.budget_services import check_budget_notifications

        b = nouveau_budget(
            montant="100.00", start_date=date(2026, 1, 1), report_actif=True
        )
        # Février : 0 dépensé -> 100 € reportés ; mars : 120 € sur 200 € = 60 %
        depense("120.00", _midi(date(2026, 3, 4)))
        assert check_budget_notifications(user.id, today=LE_10_MARS) == []
        assert b.derniere_alerte is None


class TestHistoriquePeriodes:
    def test_mensuel_six_derniers_mois(self, nouveau_budget, depense):
        b = nouveau_budget(montant="200.00", start_date=date(2026, 2, 1))
        depense("80.00", _midi(date(2025, 12, 5)))
        depense("150.00", _midi(date(2026, 2, 20)))
        periodes = b.historique_periodes(6, today=LE_10_MARS)
        assert [p["label"] for p in periodes] == [
            "10/2025",
            "11/2025",
            "12/2025",
            "01/2026",
            "02/2026",
            "03/2026",
        ]
        dec, fev, mars = periodes[2], periodes[4], periodes[5]
        assert dec["spent_amount"] == 80.0 and dec["before_start"] is True
        assert fev["spent_amount"] == 150.0 and fev["before_start"] is False
        assert fev["difference"] == 50.0
        assert mars["is_current"] is True

    def test_annuel(self, nouveau_budget):
        b = nouveau_budget(period="yearly", start_date=date(2026, 1, 1))
        labels = [p["label"] for p in b.historique_periodes(3, today=LE_10_MARS)]
        assert labels == ["2024", "2025", "2026"]


class TestApiNouveautes:
    def test_creation_annuelle_commence_au_1er_janvier(self, auth_client, category):
        resp = auth_client.post(
            "/api/v1/budgets",
            json={"category_id": category.id, "amount": 1200, "period": "yearly"},
        )
        assert resp.status_code == 201, resp.get_json()
        bid = resp.get_json()["budget"]["id"]
        b = auth_client.get(f"/api/v1/budgets/{bid}").get_json()["budget"]
        assert b["start_date"] == date(AUJOURD_HUI.year, 1, 1).isoformat()

    def test_creation_personnalisee_exige_les_dates(self, auth_client, category):
        resp = auth_client.post(
            "/api/v1/budgets",
            json={"category_id": category.id, "amount": 500, "period": "custom"},
        )
        assert resp.status_code == 400
        resp = auth_client.post(
            "/api/v1/budgets",
            json={
                "category_id": category.id,
                "amount": 500,
                "period": "custom",
                "start_date": "2026-07-01",
                "end_date": "2026-08-31",
                "report_actif": True,
            },
        )
        assert resp.status_code == 201, resp.get_json()
        bid = resp.get_json()["budget"]["id"]
        b = auth_client.get(f"/api/v1/budgets/{bid}").get_json()["budget"]
        assert b["end_date"] == "2026-08-31"
        assert b["report_actif"] is False  # pas de report sur une période unique

    def test_detail_renvoie_le_depense_reel(self, auth_client, nouveau_budget, depense):
        b = nouveau_budget(montant="200.00")
        depense("60.00", _midi(DEBUT_MOIS))
        detail = auth_client.get(f"/api/v1/budgets/{b.id}").get_json()["budget"]
        assert detail["spent_amount"] == 60.0
        assert "projected_amount" in detail and "daily_allowance" in detail

    def test_historique_des_modifications(self, auth_client, category):
        bid = auth_client.post(
            "/api/v1/budgets", json={"category_id": category.id, "amount": 300}
        ).get_json()["budget"]["id"]
        auth_client.put(
            f"/api/v1/budgets/{bid}",
            json={"amount": 450, "report_actif": True},
        )
        resp = auth_client.get(f"/api/v1/budgets/{bid}/history")
        assert resp.status_code == 200, resp.get_json()
        update, create = resp.get_json()["history"]
        assert create["action"] == "create"
        assert update["action"] == "update"
        assert update["changes"]["amount"] == {"old": 300.0, "new": 450.0}
        assert update["changes"]["report_actif"] == {"old": False, "new": True}

    def test_periodes(self, auth_client, nouveau_budget):
        b = nouveau_budget()
        resp = auth_client.get(f"/api/v1/budgets/{b.id}/periods?count=3")
        assert resp.status_code == 200
        assert len(resp.get_json()["periods"]) == 3

    def test_historique_et_periodes_d_un_autre_utilisateur(
        self, auth_client, admin_user, db_session
    ):
        from core.models.budget import Budget
        from core.models.category import Category

        cat = Category(user_id=admin_user.id, name="Admin", category_type="expense")
        db_session.add(cat)
        db_session.commit()
        b = Budget(
            user_id=admin_user.id,
            category_id=cat.id,
            amount=Decimal("10"),
            period="monthly",
            start_date=DEBUT_MOIS,
        )
        db_session.add(b)
        db_session.commit()
        assert auth_client.get(f"/api/v1/budgets/{b.id}/history").status_code == 404
        assert auth_client.get(f"/api/v1/budgets/{b.id}/periods").status_code == 404


class TestPageBudgets:
    def test_page_accessible(self, auth_client):
        resp = auth_client.get("/budgets/")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "js/pages/budgets.js" in html
        assert 'id="budgets-grid"' in html

    def test_page_exige_connexion(self, client):
        resp = client.get("/budgets/")
        assert resp.status_code in (302, 401)


# ── Couverture complémentaire ────────────────────────────────────────────────


class TestDashboardDepenseReelle:
    def test_resume_du_dashboard_renvoie_le_depense_reel(
        self, auth_client, nouveau_budget, depense
    ):
        # Régression : le dashboard lisait budgets.spent_amount, jamais mise à
        # jour, et affichait 0 € dépensé
        b = nouveau_budget(montant="300.00")
        depense("120.00", _midi(DEBUT_MOIS))
        resp = auth_client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200, resp.get_json()
        (budget,) = [x for x in resp.get_json()["budgets"] if x["id"] == b.id]
        assert budget["spent"] == 120.0


class TestReportAnnuel:
    def test_reste_de_l_annee_precedente_reporte(self, nouveau_budget, depense):
        b = nouveau_budget(
            montant="1200.00",
            period="yearly",
            start_date=date(2025, 1, 1),
            report_actif=True,
        )
        depense("1000.00", _midi(date(2025, 6, 1)))
        assert b.periode_precedente(LE_10_MARS) == (
            date(2025, 1, 1),
            date(2025, 12, 31),
        )
        assert b.montant_report(LE_10_MARS) == 200.0
        assert b.indicateurs(LE_10_MARS)["available_amount"] == 1400.0


class TestModificationVersPersonnalise:
    def test_passage_en_personnalise_desactive_le_report(self, auth_client, category):
        bid = auth_client.post(
            "/api/v1/budgets",
            json={"category_id": category.id, "amount": 300, "report_actif": True},
        ).get_json()["budget"]["id"]
        assert auth_client.get(f"/api/v1/budgets/{bid}").get_json()["budget"][
            "report_actif"
        ]

        resp = auth_client.put(
            f"/api/v1/budgets/{bid}",
            json={
                "period": "custom",
                "start_date": "2026-07-01",
                "end_date": "2026-08-31",
            },
        )
        assert resp.status_code == 200, resp.get_json()
        b = auth_client.get(f"/api/v1/budgets/{bid}").get_json()["budget"]
        assert b["period"] == "custom"
        assert b["end_date"] == "2026-08-31"
        assert b["report_actif"] is False


class TestTotauxDuResume:
    def test_totaux_sur_les_budgets_actifs_uniquement(
        self, auth_client, nouveau_budget, depense, db_session, user
    ):
        from core.models.category import Category

        actif = nouveau_budget(montant="200.00")
        depense("50.00", _midi(DEBUT_MOIS))

        # Budget qui ne commence que le mois prochain : hors des totaux
        autre = Category(user_id=user.id, name="Futur", category_type="expense")
        db_session.add(autre)
        db_session.commit()
        from core.models.budget import Budget

        db_session.add(
            Budget(
                user_id=user.id,
                category_id=autre.id,
                amount=Decimal("999.00"),
                period="monthly",
                start_date=DEBUT_MOIS + relativedelta(months=1),
            )
        )
        db_session.commit()

        data = auth_client.get("/api/v1/budgets/summary").get_json()
        summary = data["summary"]
        (b,) = [x for x in data["budgets"] if x["id"] == actif.id]
        assert len(data["budgets"]) == 2
        assert summary["total_budgets"] == 1
        assert summary["total_budget_amount"] == 200.0
        assert summary["total_spent"] == 50.0
        assert summary["total_remaining"] == 150.0
        assert summary["total_projected"] == b["projected_amount"]
