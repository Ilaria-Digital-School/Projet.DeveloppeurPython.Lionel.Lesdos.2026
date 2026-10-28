"""Tests unitaires pour le modèle Account."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.unit


class TestAccountCreation:
    """Tests de création de compte."""

    def test_create_account(self, account):
        assert account.id is not None
        assert account.name == "Compte Courant Test"

    def test_account_repr(self, account):
        r = repr(account)
        assert "Compte Courant Test" in r
        assert "courant" in r

    def test_account_user_id(self, account, user):
        assert account.user_id == user.id


class TestAccountProperties:
    """Tests des propriétés balance, currency, account_type."""

    def test_balance_default(self, app, db_session, user):
        from core.models.account import Account

        acc = Account(user_id=user.id, name="Default Balance")
        db_session.add(acc)
        db_session.flush()
        assert acc.balance == Decimal("0.00")

    def test_balance_set(self, account):
        assert account.balance == Decimal("1500.00")

    def test_balance_setter_float(self, account):
        account.balance = 2000.50
        assert account.balance == Decimal("2000.50")

    def test_balance_setter_none(self, account):
        account.balance = None
        assert account.balance == Decimal("0.00")

    def test_balance_setter_invalid(self, account):
        with pytest.raises(ValueError):
            account.balance = "not_a_number"

    def test_currency_default(self, app, db_session, user):
        from core.models.account import Account

        acc = Account(user_id=user.id, name="Defaut Currency")
        db_session.add(acc)
        db_session.flush()
        assert acc.currency == "EUR"

    def test_currency_setter_valid(self, account):
        account.currency = "usd"
        assert account.currency == "USD"

    def test_currency_setter_invalid(self, account):
        with pytest.raises(ValueError):
            account.currency = "EURO"

    def test_account_type_default(self, app, db_session, user):
        from core.models.account import Account

        acc = Account(user_id=user.id, name="Type default")
        db_session.add(acc)
        db_session.flush()
        assert acc.account_type == "courant"

    def test_account_type_setter_invalid(self, account):
        with pytest.raises(ValueError):
            account.account_type = 123


class TestAccountAliases:
    """Tests des alias français."""

    def test_nom_banque_alias(self, account):
        assert account.nom_banque == account.name
        account.nom_banque = "Nouveau Nom"
        assert account.name == "Nouveau Nom"

    def test_solde_actuel_alias(self, account):
        assert account.solde_actuel == account.balance

    def test_devise_alias(self, account):
        assert account.devise == account.currency

    def test_utilisateur_id_alias(self, account, user):
        assert account.utilisateur_id == user.id


class TestAccountToDict:
    """Tests de sérialisation."""

    def test_to_dict_keys(self, account):
        d = account.to_dict()
        expected = {
            "id",
            "user_id",
            "name",
            "account_type",
            "balance",
            "overdraft_limit",
            "currency",
            "iban",
            "bic_swift",
            "is_active",
            "is_primary",
            "notes",
            "created_at",
            "updated_at",
        }
        assert expected == set(d.keys())

    def test_to_dict_balance_float(self, account):
        d = account.to_dict()
        assert isinstance(d["balance"], float)
        assert d["balance"] == 1500.0

    def test_to_dict_currency(self, account):
        d = account.to_dict()
        assert d["currency"] == "EUR"
