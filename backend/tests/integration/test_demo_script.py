"""Le compte démo (scripts/create_demo_user.py) respecte les règles de l'appli :
montants positifs, statut 'completed', soldes cohérents, budgets exploitables."""

from datetime import datetime

import pytest

from core.extensions import db
from scripts import create_demo_user as demo

pytestmark = pytest.mark.integration


@pytest.fixture
def compte_demo(app, db_session):
    # Le script ouvre sa propre connexion psycopg2 et commite : les tables sont
    # vidées après chaque test par la fixture db_session
    url = app.config["SQLALCHEMY_DATABASE_URI"].replace("+psycopg2", "")
    assert demo.create_demo_user(url, "Demo-Test-2026!") is True
    db.session.expire_all()

    from core.models.user import User

    return User.query.filter_by(email=demo.DEMO_EMAIL).one()


def test_transactions_au_format_de_l_appli(compte_demo):
    from core.models.transactions import Transaction

    transactions = Transaction.query.filter_by(user_id=compte_demo.id).all()
    assert len(transactions) > 40
    assert all(t.montant > 0 for t in transactions)
    assert {t.statut for t in transactions} == {"completed"}
    assert all(t.date_heure_transaction <= datetime.now() for t in transactions)


def test_virements_vers_le_livret(compte_demo):
    from core.models.transactions import Transaction, TransactionType

    virements = Transaction.query.filter(
        Transaction.user_id == compte_demo.id,
        Transaction.type_transaction.in_(TransactionType.transfer_values()),
    ).all()
    assert virements
    assert all(
        v.destination_account_id and v.destination_account_id != v.account_id
        for v in virements
    )


def test_soldes_coherents(compte_demo):
    from core.services.accounts.balance_check import soldes_attendus

    soldes = soldes_attendus(compte_demo.id)
    assert len(soldes) == 3
    for s in soldes:
        assert s["ecart"] == 0, s
    livret = next(s for s in soldes if "Livret" in s["name"])
    assert livret["initial_balance"] == 7600
    assert livret["balance"] > 7600  # alimenté par les virements mensuels


def test_budgets_exploitables(compte_demo):
    from core.models.budget import Budget

    budgets = Budget.query.filter_by(user_id=compte_demo.id).all()
    assert len(budgets) == 6
    for b in budgets:
        i = b.indicateurs()
        assert i["active"]
        assert i["spent_amount"] >= 0
        assert i["projected_amount"] >= 0
        assert 0 <= i["carryover_amount"] <= float(b.amount)
        # Le budget a un historique (début il y a 2 mois)
        assert any(not p["before_start"] for p in b.historique_periodes(3)[:-1])
    assert any(b.report_actif for b in budgets)


def test_relance_idempotente(app, compte_demo):
    """Relancer le script remplace le compte démo au lieu de le dupliquer."""
    from core.models.user import User

    url = app.config["SQLALCHEMY_DATABASE_URI"].replace("+psycopg2", "")
    assert demo.create_demo_user(url, "Demo-Test-2026!") is True
    db.session.expire_all()
    assert User.query.filter_by(email=demo.DEMO_EMAIL).count() == 1
