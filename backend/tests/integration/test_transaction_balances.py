"""Tests d'intégration : cohérence du solde des comptes (création, édition, suppression).

Invariant : créer puis supprimer une transaction ramène le solde à sa valeur
initiale, et éditer une transaction applique exactement la différence.
"""

from decimal import Decimal

import pytest

from core.extensions import db
from core.services.transactions.transaction_services import TransactionService

pytestmark = pytest.mark.integration

SOLDE_INITIAL = Decimal("1500.00")


def _solde(account_id):
    """Relit solde_actuel en base (les services le modifient en SQL brut)."""
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


def _creer(user, account, montant, type_transaction, frais="0.00"):
    return TransactionService.create_transaction(
        user_id=user.id,
        account_id=account.id,
        amount=Decimal(montant),
        transaction_type=type_transaction,
        description="Test solde",
        fees=Decimal(frais),
    )


class TestSoldeCreation:
    """La création débite les dépenses (+ frais) et crédite les revenus (- frais)."""

    def test_depense_debite_montant_et_frais(self, user, account):
        _creer(user, account, "100.00", "achat", frais="2.00")
        assert _solde(account.id) == SOLDE_INITIAL - Decimal("102.00")

    def test_revenu_credite_montant_moins_frais(self, user, account):
        _creer(user, account, "100.00", "salaire", frais="2.00")
        assert _solde(account.id) == SOLDE_INITIAL + Decimal("98.00")

    def test_depense_solde_insuffisant_refusee(self, user, account):
        from core.services.transactions.transaction_services import (
            InsufficientFundsError,
        )

        with pytest.raises(InsufficientFundsError):
            _creer(user, account, "2000.00", "achat")
        assert _solde(account.id) == SOLDE_INITIAL


class TestSoldeSuppression:
    """Supprimer une transaction annule exactement son effet sur le solde."""

    @pytest.mark.parametrize(
        "type_transaction",
        # Types historiques présents en base (types mixtes)
        ["achat", "ACHAT", "expense", "salaire", "SALAIRE", "income"],
    )
    def test_creer_puis_supprimer_restaure_le_solde(
        self, user, account, type_transaction
    ):
        t = _creer(user, account, "100.00", type_transaction)
        TransactionService.delete_transaction(t.id, user.id)
        assert _solde(account.id) == SOLDE_INITIAL

    @pytest.mark.parametrize("type_transaction", ["achat", "salaire"])
    def test_creer_puis_supprimer_avec_frais_restaure_le_solde(
        self, user, account, type_transaction
    ):
        t = _creer(user, account, "100.00", type_transaction, frais="2.00")
        TransactionService.delete_transaction(t.id, user.id)
        assert _solde(account.id) == SOLDE_INITIAL


class TestSoldeEdition:
    """Éditer une transaction applique la différence (effet nouveau - effet ancien)."""

    def test_modifier_montant_depense(self, user, account):
        t = _creer(user, account, "100.00", "achat")
        assert TransactionService.update_transaction(
            t.id, user.id, montant=Decimal("150.00")
        )
        assert _solde(account.id) == SOLDE_INITIAL - Decimal("150.00")

    def test_changer_depense_en_revenu(self, user, account):
        t = _creer(user, account, "100.00", "achat")
        assert TransactionService.update_transaction(
            t.id, user.id, type_transaction="salaire"
        )
        assert _solde(account.id) == SOLDE_INITIAL + Decimal("100.00")

    def test_modifier_libelle_ne_touche_pas_au_solde(self, user, account):
        t = _creer(user, account, "100.00", "achat")
        assert TransactionService.update_transaction(t.id, user.id, libelle="Autre")
        assert _solde(account.id) == SOLDE_INITIAL - Decimal("100.00")

    def test_editer_puis_supprimer_restaure_le_solde(self, user, account):
        t = _creer(user, account, "100.00", "achat")
        TransactionService.update_transaction(t.id, user.id, montant=Decimal("40.00"))
        TransactionService.delete_transaction(t.id, user.id)
        assert _solde(account.id) == SOLDE_INITIAL

    def test_changement_de_compte_ne_plante_pas(self, user, account, db_session):
        """Cas non réconcilié (changement de compte) : doit être géré sans erreur."""
        from core.models.account import Account

        autre = Account(
            user_id=user.id,
            name="Livret",
            account_type="courant",
            balance=Decimal("0.00"),
            currency="EUR",
        )
        db_session.add(autre)
        db_session.commit()
        t = _creer(user, account, "100.00", "achat")
        assert TransactionService.update_transaction(t.id, user.id, account_id=autre.id)


@pytest.fixture
def livret(db_session, user):
    """Second compte de l'utilisateur, destination des virements."""
    from core.models.account import Account

    acc = Account(
        user_id=user.id,
        name="Livret Test",
        account_type="courant",
        balance=Decimal("200.00"),
        currency="EUR",
    )
    db_session.add(acc)
    db_session.flush()
    return acc


def _virement_api(client, source, destination, montant="100.00", type_="virement"):
    """Crée un virement comme le fait le frontend (transactions.js)."""
    return client.post(
        "/api/v1/transactions",
        json={
            "type": type_,
            "amount": montant,
            "date": "2026-06-01",
            "description": "Virement test",
            "account_id": source.id,
            "destination_account_id": destination.id,
        },
    )


class TestSoldeVirement:
    """Un virement débite le compte source et crédite le compte destination."""

    @pytest.mark.parametrize("type_", ["virement", "transfer"])
    def test_virement_met_a_jour_les_deux_comptes(
        self, auth_client, account, livret, type_
    ):
        resp = _virement_api(auth_client, account, livret, type_=type_)
        assert resp.status_code == 201
        assert _solde(account.id) == SOLDE_INITIAL - Decimal("100.00")
        assert _solde(livret.id) == Decimal("300.00")

    def test_virement_enregistre_le_compte_destination(
        self, auth_client, account, livret
    ):
        from core.models.transactions import Transaction

        resp = _virement_api(auth_client, account, livret)
        t = db.session.get(Transaction, resp.get_json()["transaction_id"])
        assert t.destination_account_id == livret.id

    def test_supprimer_virement_restaure_les_deux_comptes(
        self, auth_client, account, livret
    ):
        resp = _virement_api(auth_client, account, livret)
        tid = resp.get_json()["transaction_id"]
        assert auth_client.delete(f"/api/v1/transactions/{tid}").status_code == 200
        assert _solde(account.id) == SOLDE_INITIAL
        assert _solde(livret.id) == Decimal("200.00")

    def test_modifier_montant_virement(self, user, auth_client, account, livret):
        resp = _virement_api(auth_client, account, livret)
        tid = resp.get_json()["transaction_id"]
        assert TransactionService.update_transaction(
            tid, user.id, montant=Decimal("150.00")
        )
        assert _solde(account.id) == SOLDE_INITIAL - Decimal("150.00")
        assert _solde(livret.id) == Decimal("350.00")

    def test_virement_solde_insuffisant_refuse(self, auth_client, account, livret):
        resp = _virement_api(auth_client, account, livret, montant="5000.00")
        assert resp.status_code == 400
        assert _solde(account.id) == SOLDE_INITIAL
        assert _solde(livret.id) == Decimal("200.00")

    def test_virement_vers_le_meme_compte_refuse(self, auth_client, account):
        resp = _virement_api(auth_client, account, account)
        assert resp.status_code == 400
        assert _solde(account.id) == SOLDE_INITIAL
