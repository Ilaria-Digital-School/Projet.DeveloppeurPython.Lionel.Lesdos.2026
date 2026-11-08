"""Tests unitaires pour le modèle User."""

import pytest

pytestmark = pytest.mark.unit


class TestUserCreation:
    """Tests de création d'utilisateur."""

    def test_create_user(self, app, db_session):
        from core.models.user import User

        u = User(username="newuser", email="new@example.com")
        u.password = "MySecurePass1!"
        db_session.add(u)
        db_session.flush()
        assert u.id is not None
        assert u.username == "newuser"
        assert u.email == "new@example.com"

    def test_user_repr(self, user):
        assert "testuser" in repr(user)

    def test_user_is_active_default(self, user):
        assert user.is_active is True

    def test_user_email_verified(self, user):
        assert user.email_verified is True


class TestUserPassword:
    """Tests du hachage et vérification de mot de passe."""

    def test_password_setter_hashes(self, app, db_session):
        from core.models.user import User

        u = User(username="hashtest", email="hash@test.com")
        u.password = "plaintextpass"
        assert u.password_hash is not None
        assert u.password_hash != "plaintextpass"
        assert u.password_hash.startswith("pbkdf2:sha256")

    def test_password_not_readable(self, user):
        with pytest.raises(AttributeError):
            _ = user.password

    def test_check_password_correct(self, user):
        assert user.check_password("TestPassword123!") is True

    def test_check_password_wrong(self, user):
        assert user.check_password("WrongPassword") is False

    def test_check_password_empty(self, user):
        assert user.check_password("") is False

    def test_check_password_werkzeug(self, user):
        assert user.check_password("TestPassword123!") is True

    def test_check_password_bcrypt_format(self, app, db_session):
        """Test que check_password gère le format bcrypt $2b$."""
        from core.extensions import bcrypt
        from core.models.user import User

        u = User(username="bcryptuser", email="bcrypt@test.com")
        u.password_hash = bcrypt.generate_password_hash("bcryptpass").decode("utf-8")
        db_session.add(u)
        db_session.flush()
        assert u.check_password("bcryptpass") is True
        assert u.check_password("wrongpass") is False


class TestUserRoles:
    """Tests des rôles utilisateur."""

    def test_user_has_no_roles_by_default(self, user):
        assert user.roles == []

    def test_has_role_false(self, user):
        assert user.has_role("admin") is False

    def test_admin_user_has_role(self, admin_user):
        assert admin_user.has_role("admin") is True

    def test_is_admin_property(self, admin_user):
        assert admin_user.is_admin is True

    def test_is_admin_false(self, user):
        assert user.is_admin is False


class TestUserToDict:
    """Tests de sérialisation."""

    def test_to_dict_keys(self, user):
        d = user.to_dict()
        expected_keys = {
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "address",
            "city",
            "postal_code",
            "country",
            "language",
            "timezone",
            "is_active",
            "email_verified",
            "created_at",
            "updated_at",
            "last_login",
            "roles",
        }
        assert expected_keys == set(d.keys())

    def test_to_dict_values(self, user):
        d = user.to_dict()
        assert d["username"] == "testuser"
        assert d["email"] == "test@example.com"
        assert d["is_active"] is True
        assert d["roles"] == []

    def test_to_dict_no_password(self, user):
        d = user.to_dict()
        assert "password" not in d
        assert "password_hash" not in d


class TestUserFullName:
    """Tests du nom complet."""

    def test_full_name_both(self, app, db_session):
        from core.models.user import User

        u = User(
            username="fntest",
            email="fn@test.com",
            first_name="Jean",
            last_name="Dupont",
        )
        u.password = "pass"
        db_session.add(u)
        db_session.flush()
        assert u.full_name() == "Jean Dupont"

    def test_full_name_first_only(self, app, db_session):
        from core.models.user import User

        u = User(username="fntest2", email="fn2@test.com", first_name="Jean")
        u.password = "pass"
        db_session.add(u)
        db_session.flush()
        assert u.full_name() == "Jean"

    def test_full_name_fallback_username(self, user):
        assert user.full_name() == "testuser"
