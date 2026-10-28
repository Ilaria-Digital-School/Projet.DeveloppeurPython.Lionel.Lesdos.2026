"""Tests du gestionnaire de sessions (modules/profile/session_manager.py)."""

import pytest

from core.extensions import db
from core.models.session import UserSession
from modules.profile.session_manager import SessionManager

pytestmark = pytest.mark.unit


@pytest.fixture
def mgr(db_session):
    return SessionManager()


def _new_session(mgr, user):
    """Cree une session et renvoie son id (user_agent/ip explicites : pas de
    contexte de requete requis)."""
    info = mgr.create_session_token(user.id, user_agent="UA", ip_address="1.2.3.4")
    return info["session_id"]


class TestCreateSessionToken:
    def test_creates_session(self, mgr, user):
        info = mgr.create_session_token(user.id, user_agent="UA", ip_address="1.2.3.4")
        assert info["user_id"] == user.id
        assert info["session_id"]
        assert "expires_at" in info

        session = db.session.get(UserSession, info["session_id"])
        assert session is not None
        assert session.is_active is True
        assert session.user_id == user.id


class TestValidateSessionToken:
    def test_valid(self, mgr, user):
        sid = _new_session(mgr, user)
        assert mgr.validate_session_token(sid, user.id) is True

    def test_missing_args(self, mgr, user):
        assert mgr.validate_session_token(None, user.id) is False
        assert mgr.validate_session_token("abc", None) is False

    def test_wrong_user(self, mgr, user):
        sid = _new_session(mgr, user)
        assert mgr.validate_session_token(sid, user.id + 1000) is False

    def test_revoked_session(self, mgr, user):
        sid = _new_session(mgr, user)
        mgr.revoke_session(sid, user.id)
        assert mgr.validate_session_token(sid, user.id) is False


class TestRevoke:
    def test_revoke_session(self, mgr, user):
        sid = _new_session(mgr, user)
        mgr.revoke_session(sid, user.id)
        assert db.session.get(UserSession, sid).is_active is False

    def test_revoke_all_except_one(self, mgr, user):
        keep = _new_session(mgr, user)
        other = _new_session(mgr, user)

        mgr.revoke_all_sessions(user.id, exclude_session_id=keep)

        assert db.session.get(UserSession, keep).is_active is True
        assert db.session.get(UserSession, other).is_active is False


class TestActiveSessions:
    def test_get_active_sessions(self, mgr, user, app):
        _new_session(mgr, user)
        # get_active_sessions lit request.session_id -> contexte de requete requis
        with app.test_request_context():
            sessions = mgr.get_active_sessions(user.id)
        assert len(sessions) == 1
        assert "is_current" in sessions[0]


class TestRefreshToken:
    def test_create_refresh_token(self, mgr, user):
        info = mgr.create_refresh_token(user.id)
        assert info["token"]
        assert "expires_at" in info

    def test_verify_refresh_token_stub(self, mgr, user):
        # Implementation stub : renvoie toujours True
        assert mgr.verify_refresh_token("n-importe-quoi", user.id) is True
