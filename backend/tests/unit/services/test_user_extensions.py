"""Tests du service utilisateur etendu (core/services/user/user_extensions.py)."""

import pytest

from core.services.user.user_extensions import UserService

pytestmark = pytest.mark.unit


@pytest.fixture
def svc(db_session):
    return UserService()


class TestUpdateUserProfile:
    def test_updates_fields(self, svc, user):
        updated = svc.update_user_profile(
            user.id,
            {"first_name": "Jean", "last_name": "Dupont", "phone": "+33123456789"},
        )
        assert updated is not None
        assert updated.first_name == "Jean"
        assert updated.last_name == "Dupont"
        assert updated.phone == "+33123456789"

    def test_unknown_user_returns_none(self, svc):
        assert svc.update_user_profile(999999, {"first_name": "X"}) is None


class TestDeactivateUser:
    def test_success(self, svc, user):
        assert svc.deactivate_user(user.id, reason="demande utilisateur") is True
        assert user.is_active is False
        assert user.deactivation_reason == "demande utilisateur"

    def test_unknown_user(self, svc):
        assert svc.deactivate_user(999999) is False
