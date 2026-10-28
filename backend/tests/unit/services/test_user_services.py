"""Tests du service de gestion des utilisateurs (UserService)."""

import pytest

from core.services.user.services import UserService

pytestmark = pytest.mark.unit


@pytest.fixture
def svc(db_session):
    """Instance de UserService (contexte d'app fourni par db_session)."""
    return UserService()


class TestLookups:
    def test_get_by_id(self, svc, user):
        assert svc.get_user_by_id(user.id).id == user.id

    def test_get_by_id_unknown(self, svc):
        assert svc.get_user_by_id(999999) is None

    def test_get_by_email_case_insensitive(self, svc, user):
        assert svc.get_user_by_email("TEST@EXAMPLE.COM").id == user.id

    def test_get_by_username_case_insensitive(self, svc, user):
        assert svc.get_user_by_username("TESTUSER").id == user.id


class TestCreateUser:
    def test_create_user_success(self, svc):
        created = svc.create_user(
            username="alice",
            email="alice@example.com",
            password="AlicePass123!",
            first_name="Alice",
        )
        assert created is not None
        assert created.id is not None
        assert svc.get_user_by_username("alice").id == created.id
        assert created.check_password("AlicePass123!")

    def test_create_duplicate_username_returns_none(self, svc, user):
        assert (
            svc.create_user(
                username="testuser",
                email="other@example.com",
                password="OtherPass123!",
            )
            is None
        )

    def test_create_duplicate_email_returns_none(self, svc, user):
        assert (
            svc.create_user(
                username="autre",
                email="test@example.com",
                password="OtherPass123!",
            )
            is None
        )


class TestUpdateUser:
    def test_update_fields(self, svc, user):
        updated = svc.update_user(user.id, {"first_name": "Bob"})
        assert updated.first_name == "Bob"

    def test_update_password(self, svc, user):
        svc.update_user(user.id, {"password": "BrandNewPass123!"})
        assert user.check_password("BrandNewPass123!")

    def test_update_ignores_protected_fields(self, svc, user):
        original_id = user.id
        updated = svc.update_user(user.id, {"id": 424242})
        assert updated.id == original_id

    def test_update_unknown_user_returns_none(self, svc):
        assert svc.update_user(999999, {"first_name": "X"}) is None


class TestDeactivateAndDelete:
    def test_deactivate(self, svc, user):
        assert svc.deactivate_user(user.id, reason="demande") is True
        assert user.is_active is False

    def test_deactivate_unknown(self, svc):
        assert svc.deactivate_user(999999) is False

    def test_delete(self, svc, user):
        uid = user.id
        assert svc.delete_user(uid) is True
        assert svc.get_user_by_id(uid) is None

    def test_delete_unknown(self, svc):
        assert svc.delete_user(999999) is False


class TestUpdateLastLogin:
    def test_increments_login_count(self, svc, user):
        before = user.login_count or 0
        assert svc.update_last_login(user.id, ip_address="1.2.3.4") is True
        assert (user.login_count or 0) == before + 1
        assert user.current_login_ip == "1.2.3.4"

    def test_unknown_user(self, svc):
        assert svc.update_last_login(999999, ip_address="1.2.3.4") is False


class TestChangePassword:
    def test_too_short(self, svc, user):
        res = svc.change_password(user.id, "TestPassword123!", "court")
        assert res["success"] is False
        assert res["code"] == "PASSWORD_TOO_SHORT"

    def test_user_not_found(self, svc):
        res = svc.change_password(999999, "whatever12345", "NewPassword123!")
        assert res["success"] is False
        assert res["code"] == "USER_NOT_FOUND"

    def test_wrong_current_password(self, svc, user):
        res = svc.change_password(user.id, "MauvaisMotDePasse1", "NewPassword123!")
        assert res["success"] is False
        assert res["code"] == "INVALID_CURRENT_PASSWORD"

    def test_same_as_old(self, svc, user):
        res = svc.change_password(user.id, "TestPassword123!", "TestPassword123!")
        assert res["success"] is False
        assert res["code"] == "SAME_AS_OLD_PASSWORD"

    def test_success(self, svc, user):
        res = svc.change_password(user.id, "TestPassword123!", "NewPassword456!")
        assert res["success"] is True
        assert res["code"] == "SUCCESS"
        assert user.check_password("NewPassword456!")
