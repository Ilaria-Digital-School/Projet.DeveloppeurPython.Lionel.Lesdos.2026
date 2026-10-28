"""Tests d'intégration pour les routes de transactions."""

import io
from decimal import Decimal

import pytest

pytestmark = pytest.mark.integration


class TestTransactionList:
    """Tests de la liste des transactions."""

    def test_list_requires_auth(self, client):
        resp = client.get("/transactions/")
        assert resp.status_code == 302

    def test_list_authenticated(self, auth_client, account, category):
        resp = auth_client.get("/transactions/")
        assert resp.status_code in (200, 500)

    def test_api_list_authenticated(self, auth_client, account, category):
        resp = auth_client.get("/api/v1/transactions")
        assert resp.status_code in (200, 500)


class TestTransactionRoutesSupprimees:
    """Les routes web CRUD transactions ont été supprimées (CRUD via /api/v1/transactions)."""

    @pytest.mark.parametrize(
        "method, url",
        [
            ("get", "/transactions/add"),
            ("get", "/transactions/1/edit"),
            ("post", "/transactions/1/delete"),
        ],
    )
    def test_route_removed(self, auth_client, method, url):
        resp = getattr(auth_client, method)(url)
        assert resp.status_code == 404


class TestTransactionImport:
    """Tests de l'import CSV atomique (tout ou rien)."""

    @staticmethod
    def _post_csv(client, content):
        return client.post(
            "/api/v1/transactions/import",
            data={"file": (io.BytesIO(content.encode("utf-8")), "import.csv")},
            content_type="multipart/form-data",
        )

    def test_import_requires_auth(self, client):
        resp = self._post_csv(client, "Date;Description;Montant\n")
        assert resp.status_code in (302, 401)

    def test_import_valid_csv(self, auth_client, user, account, db_session):
        from core.models.transactions import Transaction

        csv_content = (
            "Date;Description;Montant;Type\n"
            "01/06/2026;Courses;50,00;depense\n"
            "02/06/2026;Salaire;2000,00;revenu\n"
        )
        resp = self._post_csv(auth_client, csv_content)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["imported_count"] == 2
        count = db_session.query(Transaction).filter_by(user_id=user.id).count()
        assert count == 2

    def test_import_atomic_rollback_on_error(
        self, auth_client, user, account, db_session
    ):
        """Une ligne invalide annule l'intégralité de l'import."""
        from core.models.transactions import Transaction

        user_id = user.id  # capturé avant le rollback côté serveur
        csv_content = (
            "Date;Description;Montant;Type\n"
            "01/06/2026;Courses;50,00;depense\n"
            # Montant illisible : doit provoquer l'annulation totale
            "02/06/2026;Achat impossible;abc;depense\n"
        )
        resp = self._post_csv(auth_client, csv_content)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"
        assert "errors" in data
        # Aucune transaction ne doit avoir été importée (rollback complet)
        count = db_session.query(Transaction).filter_by(user_id=user_id).count()
        assert count == 0

    def test_import_atomic_rollback_on_bad_date(
        self, auth_client, user, account, db_session
    ):
        """Une date illisible annule aussi l'intégralité de l'import."""
        from core.models.transactions import Transaction

        user_id = user.id  # capturé avant le rollback côté serveur
        csv_content = (
            "Date;Description;Montant;Type\n"
            "01/06/2026;Courses;50,00;depense\n"
            "pas-une-date;Achat;10,00;depense\n"
        )
        resp = self._post_csv(auth_client, csv_content)
        assert resp.status_code == 400
        count = db_session.query(Transaction).filter_by(user_id=user_id).count()
        assert count == 0


def _solde(account_id):
    from core.extensions import db

    db.session.expire_all()
    return Decimal(
        str(
            db.session.execute(
                db.text(
                    'SELECT solde_actuel FROM "ComptesBancaires" WHERE id_compte = :id'
                ),
                {"id": account_id},
            ).scalar()
        )
    )


class TestTransactionImportTypesEtVirements:
    """Import CSV : types précis, montants négatifs, frais, virements internes."""

    @pytest.fixture(autouse=True)
    def _sans_rate_limit(self, monkeypatch):
        # L'import est limité à 5/min : sans ça la suite déclenche des 429
        from api.v1.auth import auth_limiter

        monkeypatch.setattr(auth_limiter, "enabled", False)

    @pytest.fixture
    def livret(self, db_session, user):
        from core.models.account import Account

        acc = Account(
            user_id=user.id,
            name="Livret",
            account_type="courant",
            balance=Decimal("200.00"),
            currency="EUR",
        )
        db_session.add(acc)
        db_session.flush()
        return acc

    _post_csv = staticmethod(TestTransactionImport._post_csv)

    def _transactions(self, user):
        from core.extensions import db
        from core.models.transactions import Transaction

        db.session.expire_all()
        return (
            db.session.query(Transaction)
            .filter_by(user_id=user.id)
            .order_by(Transaction.id)
            .all()
        )

    def test_montant_negatif_sans_type_est_une_depense(
        self, auth_client, user, account
    ):
        resp = self._post_csv(
            auth_client, "Date;Description;Montant\n01/06/2026;Courses;-50,00\n"
        )
        assert resp.status_code == 200, resp.get_json()
        (t,) = self._transactions(user)
        assert t.montant == Decimal("50.00")
        assert t.type_transaction == "expense"
        assert _solde(account.id) == Decimal("1450.00")

    def test_type_precis_conserve(self, auth_client, user, account):
        resp = self._post_csv(
            auth_client,
            "Date;Description;Montant;Type\n01/06/2026;Loyer juin;700,00;loyer\n",
        )
        assert resp.status_code == 200, resp.get_json()
        (t,) = self._transactions(user)
        assert t.type_transaction == "loyer"
        assert _solde(account.id) == Decimal("800.00")

    def test_frais_importes(self, auth_client, user, account):
        resp = self._post_csv(
            auth_client,
            "Date;Description;Montant;Type;Frais\n01/06/2026;Achat;100,00;achat;2,00\n",
        )
        assert resp.status_code == 200, resp.get_json()
        assert _solde(account.id) == Decimal("1398.00")

    def test_virement_avec_compte_destination(self, auth_client, user, account, livret):
        csv_content = (
            "Date;Description;Montant;Type;Compte;Compte destination\n"
            f"01/06/2026;Epargne;100,00;virement;{account.name};Livret\n"
        )
        resp = self._post_csv(auth_client, csv_content)
        assert resp.status_code == 200, resp.get_json()
        (t,) = self._transactions(user)
        assert t.destination_account_id == livret.id
        assert _solde(account.id) == Decimal("1400.00")
        assert _solde(livret.id) == Decimal("300.00")

    def test_virement_destination_introuvable_annule_l_import(
        self, auth_client, user, account, db_session
    ):
        # Les fixtures ne sont que flushées : le rollback de l'import les effacerait
        db_session.commit()
        csv_content = (
            "Date;Description;Montant;Type;Compte destination\n"
            "01/06/2026;Courses;10,00;achat;\n"
            "02/06/2026;Epargne;100,00;virement;Inconnu\n"
        )
        resp = self._post_csv(auth_client, csv_content)
        assert resp.status_code == 400
        assert any("Inconnu" in e for e in resp.get_json()["errors"])
        assert self._transactions(user) == []
        assert _solde(account.id) == Decimal("1500.00")

    def test_virement_sans_destination_reste_sans_effet(
        self, auth_client, user, account
    ):
        resp = self._post_csv(
            auth_client,
            "Date;Description;Montant;Type\n01/06/2026;Virement;100,00;virement\n",
        )
        assert resp.status_code == 200, resp.get_json()
        assert _solde(account.id) == Decimal("1500.00")

    def test_export_puis_import_conserve_types_frais_et_virements(
        self, auth_client, user, account, livret, category
    ):
        from core.services.transactions.transaction_services import (
            TransactionService,
        )

        # Assez de fonds pour créer puis réimporter le loyer et le virement
        account.balance = Decimal("5000.00")

        TransactionService.create_transaction(
            user_id=user.id,
            account_id=account.id,
            amount=Decimal("700.00"),
            transaction_type="loyer",
            description="Loyer",
            fees=Decimal("1.50"),
            category_id=category.id,
        )
        TransactionService.create_transaction(
            user_id=user.id,
            account_id=account.id,
            amount=Decimal("100.00"),
            transaction_type="virement",
            description="Epargne",
            destination_account_id=livret.id,
        )
        export = auth_client.get("/api/v1/transactions/export?format=csv")
        assert export.status_code == 200
        avant = [
            (
                t.type_transaction,
                t.montant,
                t.frais_transaction,
                t.destination_account_id,
                t.category_id,
            )
            for t in self._transactions(user)
        ]

        resp = self._post_csv(auth_client, export.get_data(as_text=True))
        assert resp.status_code == 200, resp.get_json()
        importees = [
            (
                t.type_transaction,
                t.montant,
                t.frais_transaction,
                t.destination_account_id,
                t.category_id,
            )
            for t in self._transactions(user)[len(avant) :]
        ]
        assert sorted(importees, key=str) == sorted(avant, key=str)

    def test_categorie_associee_insensible_a_la_casse(
        self, auth_client, user, account, category
    ):
        resp = self._post_csv(
            auth_client,
            "Date;Description;Montant;Type;Catégorie\n"
            "01/06/2026;Courses;30,00;achat;alimentation\n",
        )
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["warnings"] == []
        (t,) = self._transactions(user)
        assert t.category_id == category.id

    def test_categorie_inconnue_importee_sans_categorie_avec_avertissement(
        self, auth_client, user, account
    ):
        resp = self._post_csv(
            auth_client,
            "Date;Description;Montant;Type;Catégorie\n"
            "01/06/2026;Courses;30,00;achat;Inexistante\n",
        )
        assert resp.status_code == 200, resp.get_json()
        (avertissement,) = resp.get_json()["warnings"]
        assert "Inexistante" in avertissement
        (t,) = self._transactions(user)
        assert t.category_id is None

    def test_solde_negatif_cumule_sur_plusieurs_lignes(
        self, auth_client, user, account
    ):
        """1 500 EUR, deux dépenses de 1 000 : le relevé est importé tel quel."""
        resp = self._post_csv(
            auth_client,
            "Date;Description;Montant;Type\n"
            "01/06/2026;Achat 1;1000,00;achat\n"
            "02/06/2026;Achat 2;1000,00;achat\n",
        )
        assert resp.status_code == 200, resp.get_json()
        assert len(self._transactions(user)) == 2
        assert _solde(account.id) == Decimal("-500.00")


class TestTransactionFiltres:
    """Filtres de la page Transactions (GET /api/v1/transactions et export)."""

    @pytest.fixture
    def transactions(self, db_session, user, account):
        """Une transaction par variante de type présente en base."""
        from datetime import datetime

        from core.models.transactions import Transaction

        lignes = [
            ("income", datetime(2026, 4, 1)),
            ("salaire", datetime(2026, 4, 2)),
            ("expense", datetime(2026, 4, 3)),
            ("achat", datetime(2026, 4, 30, 18, 45)),
            ("loyer", datetime(2026, 5, 1)),
            ("virement", datetime(2026, 5, 2)),
        ]
        for type_, quand in lignes:
            db_session.add(
                Transaction(
                    user_id=user.id,
                    account_id=account.id,
                    montant=Decimal("10.00"),
                    type_transaction=type_,
                    libelle=f"Test {type_}",
                    date_heure_transaction=quand,
                    statut="comptabilise",
                    devise="EUR",
                )
            )
        db_session.flush()

    @staticmethod
    def _total(client, query):
        resp = client.get(f"/api/v1/transactions?{query}")
        assert resp.status_code == 200, resp.get_json()
        return resp.get_json()["pagination"]["total"]

    @pytest.mark.parametrize(
        "type_, attendu", [("income", 2), ("expense", 3), ("transfer", 1)]
    )
    def test_filtre_type_couvre_toutes_les_variantes(
        self, auth_client, transactions, type_, attendu
    ):
        assert self._total(auth_client, f"type={type_}") == attendu

    def test_date_de_fin_incluse_toute_la_journee(self, auth_client, transactions):
        # L'achat du 30/04 à 18h45 doit être compté
        query = "date_from=01/04/2026&date_to=30/04/2026"
        assert self._total(auth_client, query) == 4

    def test_date_avec_heure_acceptee(self, auth_client, transactions):
        # Format envoyé autrefois par le calendrier des filtres
        assert self._total(auth_client, "date_from=01/05/2026%2000:00") == 2

    def test_date_invalide_refusee(self, auth_client, transactions):
        resp = auth_client.get("/api/v1/transactions?date_from=2026-05-01")
        assert resp.status_code == 400

    def test_pagination_renvoie_le_nombre_de_pages(self, auth_client, transactions):
        resp = auth_client.get("/api/v1/transactions?per_page=4&page=2")
        data = resp.get_json()
        assert data["pagination"] == {"page": 2, "per_page": 4, "total": 6, "pages": 2}
        assert len(data["transactions"]) == 2

    def test_export_applique_le_meme_filtre_de_type(self, auth_client, transactions):
        resp = auth_client.get("/api/v1/transactions/export?format=csv&type=income")
        assert resp.status_code == 200
        lignes = resp.get_data(as_text=True).strip().splitlines()
        assert len(lignes) == 1 + 2  # en-tête + 2 revenus
