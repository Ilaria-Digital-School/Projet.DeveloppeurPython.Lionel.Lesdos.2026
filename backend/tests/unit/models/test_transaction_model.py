"""Tests unitaires pour le modèle Transaction et TransactionType."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

pytestmark = pytest.mark.unit


class TestTransactionType:
    """Tests de l'enum TransactionType."""

    def test_salaire_is_income(self):
        from core.models.transactions import TransactionType

        assert TransactionType.SALAIRE.is_income is True

    def test_revenu_autre_is_income(self):
        from core.models.transactions import TransactionType

        assert TransactionType.REVENU_AUTRE.is_income is True

    def test_remboursement_is_income(self):
        from core.models.transactions import TransactionType

        assert TransactionType.REMBOURSEMENT.is_income is True

    def test_achat_is_expense(self):
        from core.models.transactions import TransactionType

        assert TransactionType.ACHAT.is_expense is True

    def test_loyer_is_expense(self):
        from core.models.transactions import TransactionType

        assert TransactionType.LOYER.is_expense is True

    def test_virement_is_transfer(self):
        from core.models.transactions import TransactionType

        assert TransactionType.VIREMENT.is_transfer is True

    def test_income_is_not_expense(self):
        from core.models.transactions import TransactionType

        assert TransactionType.SALAIRE.is_expense is False

    def test_get_choices(self):
        from core.models.transactions import TransactionType

        choices = TransactionType.get_choices()
        assert isinstance(choices, list)
        assert len(choices) == len(TransactionType)
        values = [c[0] for c in choices]
        assert "salaire" in values
        assert "achat" in values

    def test_display_name(self):
        from core.models.transactions import TransactionType

        assert TransactionType.SALAIRE.display_name == "Salaire"
        assert TransactionType.ACHAT.display_name == "Achat"


class TestTransactionCreation:
    """Tests de création de transactions."""

    def test_create_transaction(self, transaction):
        assert transaction.id is not None
        assert transaction.libelle == "Courses Carrefour"

    def test_transaction_amount(self, transaction):
        assert float(transaction.montant) == 42.50

    def test_transaction_type(self, transaction):
        assert transaction.type_transaction == "achat"

    def test_transaction_status(self, transaction):
        assert transaction.statut == "comptabilise"

    def test_transaction_devise(self, transaction):
        assert transaction.devise == "EUR"

    def test_transaction_repr(self, transaction):
        r = repr(transaction)
        assert "Transaction" in r


class TestTransactionToDict:
    """Tests de sérialisation."""

    def test_to_dict_keys(self, transaction):
        d = transaction.to_dict()
        expected = {
            "id",
            "user_id",
            "account_id",
            "destination_account_id",
            "category_id",
            "montant",
            "type_transaction",
            "libelle",
            "notes",
            "date_heure_transaction",
            "date_valeur",
            "frais_transaction",
            "devise",
            "statut",
            "date_creation",
            "date_mise_a_jour",
        }
        assert expected == set(d.keys())

    def test_to_dict_montant_float(self, transaction):
        d = transaction.to_dict()
        assert isinstance(d["montant"], float)


class TestTransactionFromDict:
    """Tests de création depuis un dictionnaire."""

    def test_from_dict(self, app, db_session, user, account):
        from core.models.transactions import Transaction

        data = {
            "user_id": user.id,
            "account_id": account.id,
            "montant": Decimal("100.00"),
            "type_transaction": "achat",
            "libelle": "Test from dict",
            "date_heure_transaction": datetime.now(timezone.utc).isoformat(),
        }
        t = Transaction.from_dict(data)
        assert t.libelle == "Test from dict"
        assert t.user_id == user.id
