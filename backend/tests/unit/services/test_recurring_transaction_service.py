"""Tests du service de transactions recurrentes (RecurringTransactionService)."""

from datetime import date, timedelta

import pytest

from core.models.transactions import Transaction
from core.services.recurring.recurring_transaction_service import (
    RecurringTransactionService as RTS,
)

pytestmark = pytest.mark.unit


class TestCalculateNextDate:
    def test_daily(self):
        assert RTS._calculate_next_date(date(2024, 1, 1), "daily", 1) == date(
            2024, 1, 2
        )
        assert RTS._calculate_next_date(date(2024, 1, 1), "daily", 3) == date(
            2024, 1, 4
        )

    def test_weekly_without_day(self):
        assert RTS._calculate_next_date(date(2024, 1, 1), "weekly", 1) == date(
            2024, 1, 8
        )

    def test_weekly_with_day_of_week(self):
        # 2024-01-01 est un lundi (weekday 0) ; viser mercredi (2)
        assert RTS._calculate_next_date(
            date(2024, 1, 1), "weekly", 1, day_of_week=2
        ) == date(2024, 1, 3)

    def test_weekly_same_day_jumps_interval(self):
        # Deja sur le bon jour -> saute d'une semaine
        assert RTS._calculate_next_date(
            date(2024, 1, 1), "weekly", 1, day_of_week=0
        ) == date(2024, 1, 8)

    def test_monthly_without_day(self):
        assert RTS._calculate_next_date(date(2024, 1, 15), "monthly", 1) == date(
            2024, 2, 15
        )

    def test_monthly_clamps_to_last_day(self):
        # jour 31 demande -> fevrier 2024 (bissextile) = 29
        assert RTS._calculate_next_date(
            date(2024, 1, 15), "monthly", 1, day_of_month=31
        ) == date(2024, 2, 29)

    def test_yearly(self):
        assert RTS._calculate_next_date(date(2024, 6, 1), "yearly", 1) == date(
            2025, 6, 1
        )

    def test_fallback_unknown_frequency(self):
        assert RTS._calculate_next_date(date(2024, 1, 1), "inconnue", 1) == date(
            2024, 1, 1
        ) + timedelta(days=30)


class TestCreateRecurring:
    def _base_data(self, account):
        return {
            "montant": 50,
            "account_id": account.id,
            "libelle": "Loyer",
            "frequency": "monthly",
            "start_date": date.today().isoformat(),
        }

    def test_success(self, user, account):
        ok, result, code = RTS.create_recurring(user.id, self._base_data(account))
        assert ok is True
        assert code == 201
        assert result.id is not None
        assert result.next_execution_date == date.today()

    def test_rejects_non_positive_amount(self, user, account):
        data = self._base_data(account)
        data["montant"] = 0
        ok, _msg, code = RTS.create_recurring(user.id, data)
        assert ok is False
        assert code == 400

    def test_requires_account(self, user, account):
        data = self._base_data(account)
        data.pop("account_id")
        ok, _msg, code = RTS.create_recurring(user.id, data)
        assert ok is False
        assert code == 400

    def test_requires_libelle(self, user, account):
        data = self._base_data(account)
        data["libelle"] = ""
        ok, _msg, code = RTS.create_recurring(user.id, data)
        assert ok is False
        assert code == 400

    def test_rejects_invalid_frequency(self, user, account):
        data = self._base_data(account)
        data["frequency"] = "hourly"
        ok, _msg, code = RTS.create_recurring(user.id, data)
        assert ok is False
        assert code == 400


@pytest.fixture
def recurring(user, account):
    """Une recurrence mensuelle active, premiere execution aujourd'hui."""
    ok, result, _code = RTS.create_recurring(
        user.id,
        {
            "montant": 20,
            "account_id": account.id,
            "libelle": "Abonnement",
            "frequency": "monthly",
            "start_date": date.today().isoformat(),
        },
    )
    assert ok
    return result


class TestCrudAndState:
    def test_get_user_recurring(self, user, recurring):
        items = RTS.get_user_recurring(user.id)
        assert len(items) == 1
        assert items[0].id == recurring.id

    def test_get_user_recurring_excludes_inactive(self, user, recurring):
        RTS.pause_recurring(recurring.id, user.id)
        assert RTS.get_user_recurring(user.id) == []
        assert len(RTS.get_user_recurring(user.id, include_inactive=True)) == 1

    def test_get_recurring_by_id(self, user, recurring):
        assert RTS.get_recurring_by_id(recurring.id, user.id).id == recurring.id
        assert RTS.get_recurring_by_id(999999, user.id) is None

    def test_update_success(self, user, recurring):
        ok, result, code = RTS.update_recurring(
            recurring.id, user.id, {"libelle": "Nouveau", "montant": 99}
        )
        assert ok is True and code == 200
        assert result.libelle == "Nouveau"
        assert float(result.montant) == 99.0

    def test_update_not_found(self, user):
        ok, _msg, code = RTS.update_recurring(999999, user.id, {"libelle": "X"})
        assert ok is False and code == 404

    def test_delete_success(self, user, recurring):
        ok, _msg, code = RTS.delete_recurring(recurring.id, user.id)
        assert ok is True and code == 200
        assert RTS.get_recurring_by_id(recurring.id, user.id) is None

    def test_delete_not_found(self, user):
        ok, _msg, code = RTS.delete_recurring(999999, user.id)
        assert ok is False and code == 404

    def test_pause_and_resume(self, user, recurring):
        ok, _msg, code = RTS.pause_recurring(recurring.id, user.id)
        assert ok is True and code == 200
        assert RTS.get_recurring_by_id(recurring.id, user.id).is_active is False

        ok, _msg, code = RTS.resume_recurring(recurring.id, user.id)
        assert ok is True and code == 200
        assert RTS.get_recurring_by_id(recurring.id, user.id).is_active is True

    def test_pause_not_found(self, user):
        ok, _msg, code = RTS.pause_recurring(999999, user.id)
        assert ok is False and code == 404


class TestProcessDueTransactions:
    def test_creates_transaction_and_advances_date(self, user, recurring):
        before = Transaction.query.filter_by(user_id=user.id).count()

        count = RTS.process_due_transactions()

        assert count >= 1
        after = Transaction.query.filter_by(user_id=user.id).count()
        assert after == before + 1

        refreshed = RTS.get_recurring_by_id(recurring.id, user.id)
        assert refreshed.last_executed_date == date.today()
        assert refreshed.next_execution_date > date.today()
