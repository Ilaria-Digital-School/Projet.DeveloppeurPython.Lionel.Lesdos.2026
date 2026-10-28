"""Tests unitaires pour le modèle Category."""

import pytest

pytestmark = pytest.mark.unit


class TestCategoryCreation:
    """Tests de création de catégorie."""

    def test_create_category(self, category):
        assert category.id is not None
        assert category.name == "Alimentation"

    def test_category_user_id(self, category, user):
        assert category.user_id == user.id

    def test_category_is_expense(self, category):
        assert category.is_expense is True

    def test_income_category(self, income_category):
        assert income_category.is_expense is False
        assert income_category.name == "Salaire"

    def test_category_repr(self, category):
        r = repr(category)
        assert "Alimentation" in r


class TestCategoryIsGlobal:
    """Tests de la propriété is_global."""

    def test_user_category_not_global(self, category):
        assert category.is_global is False

    def test_global_category(self, app, db_session):
        from core.models.category import Category

        cat = Category(
            user_id=None,
            name="Global Cat",
            is_expense=True,
            category_type="expense",
        )
        db_session.add(cat)
        db_session.flush()
        assert cat.is_global is True


class TestCategoryDefaults:
    """Tests des valeurs par défaut."""

    def test_default_color(self, app, db_session, user):
        from core.models.category import Category

        cat = Category(user_id=user.id, name="NoColor", is_expense=True)
        db_session.add(cat)
        db_session.flush()
        assert cat.color == "#6c757d"

    def test_default_icon(self, app, db_session, user):
        from core.models.category import Category

        cat = Category(user_id=user.id, name="NoIcon", is_expense=True)
        db_session.add(cat)
        db_session.flush()
        assert cat.icon == "tag"

    def test_custom_color(self, category):
        assert category.color == "#FF5733"

    def test_custom_icon(self, category):
        assert category.icon == "fa-shopping-cart"


class TestCategoryUniqueConstraint:
    """Tests de la contrainte d'unicité (user_id, name)."""

    def test_duplicate_name_same_user_raises(self, app, db_session, user):
        from sqlalchemy.exc import IntegrityError

        from core.models.category import Category

        cat1 = Category(user_id=user.id, name="Doublon", is_expense=True)
        db_session.add(cat1)
        db_session.flush()

        cat2 = Category(user_id=user.id, name="Doublon", is_expense=True)
        db_session.add(cat2)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_same_name_different_users(self, app, db_session, user, admin_user):
        from core.models.category import Category

        cat1 = Category(user_id=user.id, name="Partagé", is_expense=True)
        cat2 = Category(user_id=admin_user.id, name="Partagé", is_expense=True)
        db_session.add_all([cat1, cat2])
        db_session.flush()
        assert cat1.id != cat2.id


class TestCategoryToDict:
    """Tests de sérialisation."""

    def test_to_dict_keys(self, category):
        d = category.to_dict()
        expected = {
            "id",
            "user_id",
            "name",
            "description",
            "color",
            "icon",
            "is_expense",
            "monthly_budget",
            "is_default",
            "created_at",
            "updated_at",
        }
        assert expected == set(d.keys())

    def test_to_dict_values(self, category):
        d = category.to_dict()
        assert d["name"] == "Alimentation"
        assert d["is_expense"] is True
        assert d["color"] == "#FF5733"
