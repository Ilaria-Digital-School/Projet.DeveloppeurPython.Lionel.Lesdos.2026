"""Tests des transactions récurrentes : calcul des dates et exécution par le scheduler."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.extensions import db
from core.services.recurring.recurring_transaction_service import (
    RecurringTransactionService as RTS,
)

pytestmark = pytest.mark.integration

suivante = RTS._calculate_next_date


class TestCalculProchaineDate:
    def test_quotidien(self):
        assert suivante(date(2026, 6, 1), "daily", 3) == date(2026, 6, 4)

    def test_hebdomadaire_sans_jour(self):
        assert suivante(date(2026, 6, 1), "weekly", 2) == date(2026, 6, 15)

    def test_hebdomadaire_jour_fixe(self):
        # Lundi 1er juin 2026 -> mercredi suivant
        assert suivante(date(2026, 6, 1), "weekly", 1, day_of_week=2) == date(
            2026, 6, 3
        )

    def test_hebdomadaire_jour_fixe_respecte_l_intervalle(self):
        # Tous les 2 lundis, depuis le lundi 1er juin -> lundi 15 juin
        assert suivante(date(2026, 6, 1), "weekly", 2, day_of_week=0) == date(
            2026, 6, 15
        )

    def test_mensuel(self):
        assert suivante(date(2026, 6, 5), "monthly", 1, day_of_month=5) == date(
            2026, 7, 5
        )

    def test_mensuel_fin_de_mois(self):
        # Le 31 : dernier jour des mois courts, mais bien le 31 quand il existe
        assert suivante(date(2026, 1, 31), "monthly", 1, day_of_month=31) == date(
            2026, 2, 28
        )
        assert suivante(date(2026, 2, 28), "monthly", 1, day_of_month=31) == date(
            2026, 3, 31
        )

    def test_mensuel_le_30(self):
        assert suivante(date(2026, 6, 30), "monthly", 1, day_of_month=30) == date(
            2026, 7, 30
        )

    def test_annuel(self):
        assert suivante(date(2026, 6, 1), "yearly", 1) == date(2027, 6, 1)


@pytest.fixture
def recurrence(db_session, user, account):
    """Fabrique de récurrences (committées : le scheduler fait ses propres commits)."""
    from core.models.recurring_transaction import RecurringTransaction

    def fabriquer(prochaine, frequency="daily", montant="10.00", **kwargs):
        r = RecurringTransaction(
            user_id=user.id,
            account_id=account.id,
            montant=Decimal(montant),
            type_transaction=kwargs.pop("type_transaction", "abonnement"),
            libelle="Abonnement",
            frequency=frequency,
            interval=kwargs.pop("interval", 1),
            start_date=kwargs.pop("start_date", prochaine),
            next_execution_date=prochaine,
            is_active=True,
            **kwargs,
        )
        db_session.add(r)
        db_session.commit()
        return r

    return fabriquer


def _transactions(user):
    from core.models.transactions import Transaction

    db.session.expire_all()
    return (
        Transaction.query.filter_by(user_id=user.id)
        .order_by(Transaction.date_heure_transaction)
        .all()
    )


def _solde(account):
    # account.balance garde une copie en cache : relire la colonne en SQL
    db.session.expire_all()
    return Decimal(
        str(
            db.session.execute(
                db.text(
                    'SELECT solde_actuel FROM "ComptesBancaires" WHERE id_compte = :id'
                ),
                {"id": account.id},
            ).scalar()
        )
    )


class TestExecutionScheduler:
    def test_occurrence_du_jour(self, user, account, recurrence):
        aujourd_hui = date.today()
        r = recurrence(aujourd_hui)
        assert RTS.process_due_transactions() == 1
        (t,) = _transactions(user)
        assert t.date_heure_transaction.date() == aujourd_hui
        assert _solde(account) == Decimal("1490.00")
        db.session.expire_all()
        assert r.next_execution_date == aujourd_hui + timedelta(days=1)
        assert r.last_executed_date == aujourd_hui

    def test_future_non_executee(self, user, recurrence):
        recurrence(date.today() + timedelta(days=1))
        assert RTS.process_due_transactions() == 0
        assert _transactions(user) == []

    def test_rattrape_les_occurrences_manquees(self, user, account, recurrence):
        """Scheduler arrêté 3 jours : les 4 occurrences sont créées, à leur date."""
        aujourd_hui = date.today()
        r = recurrence(aujourd_hui - timedelta(days=3))
        assert RTS.process_due_transactions() == 4
        dates = [t.date_heure_transaction.date() for t in _transactions(user)]
        assert dates == [aujourd_hui - timedelta(days=n) for n in (3, 2, 1, 0)]
        assert _solde(account) == Decimal("1460.00")
        db.session.expire_all()
        assert r.next_execution_date == aujourd_hui + timedelta(days=1)

    def test_deux_executions_le_meme_jour_ne_dupliquent_pas(self, user, recurrence):
        recurrence(date.today())
        RTS.process_due_transactions()
        assert RTS.process_due_transactions() == 0
        assert len(_transactions(user)) == 1

    def test_mensuel_garde_son_jour_malgre_un_retard(self, user, recurrence):
        """Loyer du 5 traité avec 2 jours de retard : la suivante reste le 5."""
        aujourd_hui = date.today()
        prevue = aujourd_hui - timedelta(days=2)
        r = recurrence(prevue, frequency="monthly")
        RTS.process_due_transactions()
        (t,) = _transactions(user)
        assert t.date_heure_transaction.date() == prevue
        db.session.expire_all()
        assert r.next_execution_date == suivante(prevue, "monthly", 1)

    def test_date_de_fin_rattrapage_limite(self, user, recurrence):
        aujourd_hui = date.today()
        r = recurrence(
            aujourd_hui - timedelta(days=5), end_date=aujourd_hui - timedelta(days=4)
        )
        assert RTS.process_due_transactions() == 2  # J-5 et J-4 seulement
        assert len(_transactions(user)) == 2
        db.session.expire_all()
        assert r.is_active is False

    def test_echec_n_avance_pas_la_date(self, user, account, recurrence):
        """Solde insuffisant : aucune transaction, la récurrence reste due."""
        aujourd_hui = date.today()
        r = recurrence(aujourd_hui, montant="5000.00")
        assert RTS.process_due_transactions() == 0
        assert _transactions(user) == []
        assert _solde(account) == Decimal("1500.00")
        db.session.expire_all()
        assert r.next_execution_date == aujourd_hui
        assert r.is_active is True

    def test_virement_recurrent(self, user, account, recurrence, db_session):
        from core.models.account import Account

        livret = Account(
            user_id=user.id,
            name="Livret",
            account_type="courant",
            balance=Decimal("0.00"),
            currency="EUR",
        )
        db_session.add(livret)
        db_session.commit()
        recurrence(
            date.today(),
            montant="100.00",
            type_transaction="virement",
            destination_account_id=livret.id,
        )
        assert RTS.process_due_transactions() == 1
        assert _solde(account) == Decimal("1400.00")
        assert _solde(livret) == Decimal("100.00")


def _notifications(user, type_):
    from core.models.notification import Notification

    db.session.expire_all()
    return Notification.query.filter_by(user_id=user.id, notification_type=type_).all()


class TestEchecsEtNotifications:
    def test_premier_echec_previent_l_utilisateur(self, user, recurrence):
        r = recurrence(date.today(), montant="5000.00")
        RTS.process_due_transactions()
        db.session.expire_all()
        assert r.echecs_consecutifs == 1
        assert "Solde insuffisant" in r.derniere_erreur
        assert r.is_active is True
        (n,) = _notifications(user, "recurring_failed")
        assert "Abonnement" in n.message and "Solde insuffisant" in n.message

    def test_pas_de_notification_a_chaque_nouvel_echec(self, user, recurrence):
        recurrence(date.today(), montant="5000.00")
        RTS.process_due_transactions()
        RTS.process_due_transactions()
        assert len(_notifications(user, "recurring_failed")) == 1

    def test_pause_apres_trois_echecs(self, user, recurrence):
        r = recurrence(date.today(), montant="5000.00")
        for _ in range(3):
            RTS.process_due_transactions()
        db.session.expire_all()
        assert r.is_active is False
        assert r.echecs_consecutifs == 3
        notes = _notifications(user, "recurring_failed")
        assert len(notes) == 2  # premier échec + mise en pause
        assert "mise en pause" in notes[-1].message
        # Suspendue : plus retentée
        assert RTS.process_due_transactions() == 0

    def test_succes_remet_le_compteur_a_zero(self, user, account, recurrence):
        r = recurrence(date.today(), montant="2000.00")
        RTS.process_due_transactions()
        db.session.execute(
            db.text(
                'UPDATE "ComptesBancaires" SET solde_actuel = 5000 WHERE id_compte = :id'
            ),
            {"id": account.id},
        )
        db.session.commit()
        assert RTS.process_due_transactions() == 1
        db.session.expire_all()
        assert r.echecs_consecutifs == 0 and r.derniere_erreur is None

    def test_reprise_remet_le_compteur_a_zero(self, user, recurrence):
        r = recurrence(date.today(), montant="5000.00")
        for _ in range(3):
            RTS.process_due_transactions()
        ok, _msg, _code = RTS.resume_recurring(r.id, user.id)
        assert ok
        db.session.expire_all()
        assert r.is_active is True and r.echecs_consecutifs == 0

    def test_une_notification_par_recurrence_executee(self, user, recurrence):
        recurrence(date.today() - timedelta(days=2))  # 3 occurrences rattrapées
        RTS.process_due_transactions()
        (n,) = _notifications(user, "recurring_executed")
        assert "3 occurrence(s)" in n.message

    def test_alerte_budget_declenchee(self, user, category, recurrence, db_session):
        from core.models.budget import Budget

        db_session.add(
            Budget(
                user_id=user.id,
                category_id=category.id,
                amount=Decimal("100.00"),
                period="monthly",
                start_date=date.today().replace(day=1),
                notification_threshold=50,
            )
        )
        db_session.commit()
        recurrence(date.today(), montant="60.00", category_id=category.id)
        RTS.process_due_transactions()
        assert len(_notifications(user, "budget_alert")) == 1
