"""Tests du solde initial et du contrôle de cohérence des soldes.

Invariant vérifié après chaque opération : solde_actuel = solde_initial +
effet des transactions (core/services/accounts/balance_check.py).
"""

import io
from decimal import Decimal

import pytest

from core.extensions import db
from core.services.accounts.balance_check import (
    corriger_soldes,
    soldes_attendus,
    soldes_incoherents,
)
from core.services.transactions.transaction_services import TransactionService

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _sans_rate_limit(monkeypatch):
    from api.v1.auth import auth_limiter

    monkeypatch.setattr(auth_limiter, "enabled", False)


@pytest.fixture
def livret(db_session, user):
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


def _solde(account_id):
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


def _creer(user, account, montant, type_, frais="0", **kw):
    return TransactionService.create_transaction(
        user_id=user.id,
        account_id=account.id,
        amount=Decimal(montant),
        transaction_type=type_,
        description="Test",
        fees=Decimal(frais),
        **kw,
    )


def _coherent(user):
    db.session.expire_all()
    assert soldes_incoherents(user.id) == []


class TestSoldeInitial:
    def test_nouveau_compte_part_de_son_solde(self, account):
        assert account.initial_balance == Decimal("1500.00")

    def test_creation_via_api(self, auth_client, user):
        resp = auth_client.post(
            "/api/v1/comptes",
            json={
                "name": "Nouveau",
                "account_type": "checking",
                "initial_balance": "320.50",
            },
        )
        assert resp.status_code in (200, 201), resp.get_json()
        (s,) = [s for s in soldes_attendus(user.id) if s["name"] == "Nouveau"]
        assert s["initial_balance"] == Decimal("320.50")
        assert s["ecart"] == 0

    def test_saisie_manuelle_du_solde_reste_coherente(self, auth_client, user, account):
        _creer(user, account, "100.00", "achat")
        resp = auth_client.put(
            f"/api/v1/comptes/{account.id}",
            json={"name": account.name, "balance": "2000.00"},
        )
        assert resp.status_code == 200
        assert _solde(account.id) == Decimal("2000.00")
        _coherent(user)


class TestCoherenceApresOperations:
    def test_creation_suppression(self, user, account):
        t1 = _creer(user, account, "100.00", "achat", frais="2.00")
        _creer(user, account, "50.00", "salaire", frais="1.00")
        _coherent(user)
        TransactionService.delete_transaction(t1.id, user.id)
        _coherent(user)

    def test_virement(self, user, account, livret):
        t = _creer(
            user, account, "100.00", "virement", destination_account_id=livret.id
        )
        _coherent(user)
        TransactionService.delete_transaction(t.id, user.id)
        _coherent(user)

    def test_edition_montant_type_frais(self, user, account):
        t = _creer(user, account, "100.00", "achat")
        TransactionService.update_transaction(t.id, user.id, montant=Decimal("80.00"))
        TransactionService.update_transaction(t.id, user.id, type_transaction="salaire")
        TransactionService.update_transaction(
            t.id, user.id, frais_transaction=Decimal("3.00")
        )
        _coherent(user)

    def test_edition_changement_de_compte(self, user, account, livret):
        t = _creer(user, account, "100.00", "achat")
        assert TransactionService.update_transaction(
            t.id, user.id, account_id=livret.id
        )
        assert _solde(account.id) == Decimal("1500.00")
        assert _solde(livret.id) == Decimal("100.00")
        _coherent(user)

    def test_edition_depense_en_virement_et_retour(self, user, account, livret):
        t = _creer(user, account, "100.00", "achat")
        TransactionService.update_transaction(
            t.id, user.id, type_transaction="virement", destination_account_id=livret.id
        )
        assert _solde(account.id) == Decimal("1400.00")
        assert _solde(livret.id) == Decimal("300.00")
        _coherent(user)
        TransactionService.update_transaction(t.id, user.id, type_transaction="achat")
        assert _solde(account.id) == Decimal("1400.00")
        assert _solde(livret.id) == Decimal("200.00")
        _coherent(user)

    def test_import_csv(self, auth_client, user, account, livret):
        csv = (
            "Date;Description;Montant;Type;Frais;Compte destination\n"
            "01/06/2026;Courses;-40,00;;;\n"
            "02/06/2026;Salaire;900,00;revenu;;\n"
            "03/06/2026;Epargne;100,00;virement;;Livret\n"
        )
        resp = auth_client.post(
            "/api/v1/transactions/import",
            data={"file": (io.BytesIO(csv.encode()), "i.csv")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200, resp.get_json()
        _coherent(user)


class TestImportReleveCompte:
    """POST /api/v1/comptes/import : montants positifs, statut 'completed'."""

    def _importer(self, client, account):
        releve = (
            "Date;Ref;Debit;Credit;Libelle;Solde\n"
            "01/06/2026;1;75,00;;Supermarche;\n"
            "02/06/2026;2;;300,00;Virement recu;\n"
        )
        return client.post(
            "/api/v1/comptes/import",
            data={
                "file": (io.BytesIO(releve.encode()), "releve.csv"),
                "account_id": str(account.id),
            },
            content_type="multipart/form-data",
        )

    def test_format_des_transactions(self, auth_client, user, account):
        from core.models.transactions import Transaction

        resp = self._importer(auth_client, account)
        assert resp.status_code == 200, resp.get_json()
        db.session.expire_all()
        ts = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.id).all()
        assert [(t.type_transaction, t.montant, t.statut) for t in ts] == [
            ("expense", Decimal("75.00"), "completed"),
            ("income", Decimal("300.00"), "completed"),
        ]
        assert _solde(account.id) == Decimal("1725.00")
        _coherent(user)

    def test_supprimer_une_ligne_importee_restaure_le_solde(
        self, auth_client, user, account
    ):
        from core.models.transactions import Transaction

        self._importer(auth_client, account)
        db.session.expire_all()
        depense = Transaction.query.filter_by(
            user_id=user.id, type_transaction="expense"
        ).one()
        TransactionService.delete_transaction(depense.id, user.id)
        assert _solde(account.id) == Decimal("1800.00")
        _coherent(user)


class TestDetectionEtCorrection:
    def test_ecart_detecte_puis_corrige(self, user, account):
        _creer(user, account, "100.00", "achat")
        db.session.execute(
            db.text(
                'UPDATE "ComptesBancaires" SET solde_actuel = 999 WHERE id_compte = :id'
            ),
            {"id": account.id},
        )
        db.session.commit()
        (s,) = soldes_incoherents(user.id)
        assert s["expected_balance"] == Decimal("1400.00")
        assert s["ecart"] == Decimal("-401.00")
        corriger_soldes(user.id)
        assert _solde(account.id) == Decimal("1400.00")
        _coherent(user)

    def test_commande_cli(self, app, user, account):
        db.session.commit()
        runner = app.test_cli_runner()
        assert "cohérents" in runner.invoke(args=["accounts", "check-balances"]).output
        db.session.execute(
            db.text(
                'UPDATE "ComptesBancaires" SET solde_actuel = 1 WHERE id_compte = :id'
            ),
            {"id": account.id},
        )
        db.session.commit()
        res = runner.invoke(args=["accounts", "check-balances"])
        assert res.exit_code == 1
        assert "attendu 1500.00" in res.output
        res = runner.invoke(args=["accounts", "check-balances", "--fix"])
        assert res.exit_code == 0
        assert _solde(account.id) == Decimal("1500.00")


class TestImportReleveFiable:
    """POST /api/v1/comptes/import : tout ou rien, erreurs signalées."""

    ENTETE = "Date;Ref;Debit;Credit;Libelle;Solde\n"

    def _importer(
        self, client, contenu, account=None, nom="releve.csv", encodage="utf-8", **form
    ):
        data = {"file": (io.BytesIO(contenu.encode(encodage)), nom), **form}
        if account is not None:
            data["account_id"] = str(account.id)
        return client.post(
            "/api/v1/comptes/import", data=data, content_type="multipart/form-data"
        )

    def _transactions(self, user):
        from core.models.transactions import Transaction

        db.session.expire_all()
        return Transaction.query.filter_by(user_id=user.id).all()

    def test_ligne_invalide_annule_tout(self, auth_client, user, account, db_session):
        db_session.commit()
        resp = self._importer(
            auth_client,
            self.ENTETE
            + "01/06/2026;1;75,00;;Supermarche;\n32/13/2026;2;10,00;;Date fausse;\n",
            account,
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert any("Ligne 3" in e for e in data["errors"])
        assert self._transactions(user) == []
        assert _solde(account.id) == Decimal("1500.00")

    def test_compte_obligatoire(self, auth_client, account):
        resp = self._importer(auth_client, self.ENTETE + "01/06/2026;1;75,00;;X;\n")
        assert resp.status_code == 400

    def test_excel_refuse(self, auth_client, account):
        resp = self._importer(
            auth_client, "PK\x03\x04binaire", account, nom="releve.xlsx"
        )
        assert resp.status_code == 400
        assert "CSV" in resp.get_json()["message"]

    def test_fichier_sans_ligne_refuse(self, auth_client, account):
        assert self._importer(auth_client, self.ENTETE, account).status_code == 400

    def test_encodage_iso_8859_1(self, auth_client, user, account, db_session):
        db_session.commit()
        resp = self._importer(
            auth_client,
            self.ENTETE + "01/06/2026;1;20,00;;Café;\n",
            account,
            encodage="iso-8859-1",
        )
        assert resp.status_code == 200, resp.get_json()
        (t,) = self._transactions(user)
        assert t.libelle == "Café"

    def test_simulation_valide_sans_rien_creer(
        self, auth_client, user, account, db_session
    ):
        db_session.commit()
        resp = self._importer(
            auth_client,
            self.ENTETE
            + "01/06/2026;1;75,00;;Supermarche;\n02/06/2026;2;;300,00;Salaire;\n",
            account,
            dry_run="true",
        )
        assert resp.status_code == 200, resp.get_json()
        assert resp.get_json()["result"]["created_transactions"] == 2
        assert self._transactions(user) == []
        assert _solde(account.id) == Decimal("1500.00")

    def test_simulation_signale_les_erreurs(self, auth_client, account, db_session):
        db_session.commit()
        resp = self._importer(
            auth_client,
            self.ENTETE + "pas-une-date;1;75,00;;X;\n",
            account,
            dry_run="true",
        )
        assert resp.status_code == 400
        assert resp.get_json()["errors"]
