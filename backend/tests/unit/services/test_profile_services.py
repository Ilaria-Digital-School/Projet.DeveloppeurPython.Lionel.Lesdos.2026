"""Tests du service de gestion des profils (ProfileService)."""

import pytest

from core.models.user import User
from core.services.profile.profile_services import ProfileService

pytestmark = pytest.mark.unit


@pytest.fixture
def profile_svc(db_session):
    """Instance de ProfileService avec cache vide (isolation inter-tests)."""
    from core.extensions import cache

    cache.clear()
    yield ProfileService()
    cache.clear()


@pytest.fixture
def other_user(db_session):
    """Un second utilisateur, pour les tests de collision d'email."""
    u = User(username="autre", email="taken@example.com", is_active=True)
    u.password = "AutrePass123!"
    db_session.add(u)
    db_session.flush()
    return u


class TestLookups:
    def test_get_user_profile(self, profile_svc, user):
        assert profile_svc.get_user_profile(user.id).id == user.id

    def test_get_user_profile_unknown(self, profile_svc):
        assert profile_svc.get_user_profile(999999) is None

    def test_get_user_by_email(self, profile_svc, user):
        assert profile_svc.get_user_by_email("test@example.com").id == user.id

    def test_email_exists(self, profile_svc, user):
        assert profile_svc._email_exists("test@example.com") is True
        assert profile_svc._email_exists("inexistant@example.com") is False

    def test_email_exists_excludes_user(self, profile_svc, user):
        # Son propre email, exclu de la recherche -> considere comme libre
        assert (
            profile_svc._email_exists("test@example.com", exclude_user_id=user.id)
            is False
        )


class TestGetUserProfileData:
    def test_returns_dict(self, profile_svc, user):
        data = profile_svc.get_user_profile_data(user.id)
        assert data["id"] == user.id
        assert data["username"] == user.username
        assert data["email"] == user.email
        for key in ("first_name", "phone", "city", "country"):
            assert key in data

    def test_unknown_returns_empty(self, profile_svc):
        assert profile_svc.get_user_profile_data(999999) == {}


class TestUpdateProfile:
    def test_unknown_user(self, profile_svc):
        ok, _msg, code = profile_svc.update_profile(999999, {"first_name": "X"})
        assert ok is False
        assert code == 404

    def test_success_updates_fields(self, profile_svc, user):
        ok, _msg, code = profile_svc.update_profile(
            user.id, {"first_name": "Nouveau", "city": "Lyon"}
        )
        assert ok is True
        assert code == 200
        assert user.first_name == "Nouveau"
        assert user.city == "Lyon"

    def test_invalid_phone(self, profile_svc, user):
        ok, _msg, code = profile_svc.update_profile(user.id, {"phone": "abc!!!"})
        assert ok is False
        assert code == 400

    def test_duplicate_email(self, profile_svc, user, other_user):
        ok, _msg, code = profile_svc.update_profile(
            user.id, {"email": "taken@example.com"}
        )
        assert ok is False
        assert code == 400


class TestChangePassword:
    def test_unknown_user(self, profile_svc):
        ok, _msg, code = profile_svc.change_password(
            999999, "TestPassword123!", "NouveauPass123!"
        )
        assert ok is False
        assert code == 404

    def test_wrong_current(self, profile_svc, user):
        ok, _msg, code = profile_svc.change_password(
            user.id, "MauvaisMotDePasse1", "NouveauPass123!"
        )
        assert ok is False
        assert code == 400

    def test_weak_new_password(self, profile_svc, user):
        ok, _msg, code = profile_svc.change_password(
            user.id, "TestPassword123!", "faible"
        )
        assert ok is False
        assert code == 400

    def test_success(self, profile_svc, user):
        ok, _msg, code = profile_svc.change_password(
            user.id, "TestPassword123!", "NouveauPass123!"
        )
        assert ok is True
        assert code == 200
        assert user.check_password("NouveauPass123!")
