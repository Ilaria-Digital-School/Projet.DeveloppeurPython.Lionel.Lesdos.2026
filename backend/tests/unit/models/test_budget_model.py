"""Tests unitaires pour le modèle Budget."""

from datetime import date

import pytest

pytestmark = pytest.mark.unit


class TestBudgetCreation:
    """Tests de création de budget."""

    def test_create_budget(self, budget):
        assert budget.id is not None
        assert float(budget.amount) == 500.0

    def test_budget_period(self, budget):
        assert budget.period == "monthly"

    def test_budget_start_date(self, budget):
        assert budget.start_date == date.today().replace(day=1)

    def test_budget_repr(self, budget):
        r = repr(budget)
        assert "Budget" in r
        assert "500" in r


class TestBudgetRelations:
    """Tests des relations."""

    def test_budget_user_relation(self, budget, user):
        assert budget.user_id == user.id

    def test_budget_category_relation(self, budget, category):
        assert budget.category_id == category.id


class TestBudgetDefaults:
    """Tests des valeurs par défaut."""

    def test_notification_threshold_default(self, budget):
        assert budget.notification_threshold == 90

    def test_notification_sent_default(self, budget):
        assert budget.notification_sent is False

    def test_spent_amount_default(self, budget):
        assert float(budget.spent_amount or 0) == 0.0
