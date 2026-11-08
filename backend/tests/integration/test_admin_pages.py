"""Tests de rendu des pages admin + gardes anti-régression.

Couvre les changements de présentation admin :
- raccourcis et alerte suspecte sur /admin/dashboard,
- disparition de la section admin du dashboard utilisateur,
- rendu Tailwind (plus de Bootstrap mort) de la page détails utilisateur,
- absence de gestionnaires onclick= inline (bloqués par la CSP stricte).
"""

import pytest

pytestmark = pytest.mark.integration


# Pages admin rendues en HTML (hors page détails qui a besoin d'un user id)
ADMIN_PAGES = [
    "/admin/dashboard",
    "/admin/users-management",
    "/admin/monitoring",
]


class TestAdminDashboard:
    """Contenu déplacé depuis le dashboard utilisateur (option B2)."""

    def test_dashboard_has_quick_access_shortcuts(self, admin_client):
        resp = admin_client.get("/admin/dashboard")
        assert resp.status_code == 200
        assert "Gérer les utilisateurs".encode() in resp.data
        assert "Voir le monitoring".encode() in resp.data

    def test_user_dashboard_no_longer_has_admin_section(self, admin_client):
        resp = admin_client.get("/dashboard/")
        assert resp.status_code == 200
        assert "Administration Système".encode() not in resp.data


class TestUserDetailsTailwind:
    """admin/user_details.html réécrit en Tailwind (plus de Bootstrap mort)."""

    def test_renders_ok(self, admin_client, user):
        resp = admin_client.get(f"/admin/user/{user.id}")
        assert resp.status_code == 200
        assert "Détails Utilisateur".encode() in resp.data
        assert b"Actions Administratives" in resp.data

    @pytest.mark.parametrize(
        "dead_class", [b'class="row"', b"col-md-", b"d-none", b"d-flex", b"d-grid"]
    )
    def test_no_dead_bootstrap_classes(self, admin_client, user, dead_class):
        resp = admin_client.get(f"/admin/user/{user.id}")
        assert resp.status_code == 200
        assert dead_class not in resp.data


class TestNoInlineOnclick:
    """Garde CSP : aucun gestionnaire onclick= inline (bloqué en production)."""

    @pytest.mark.parametrize("path", ADMIN_PAGES)
    def test_admin_page_has_no_inline_onclick(self, admin_client, path):
        resp = admin_client.get(path)
        assert resp.status_code == 200
        assert b"onclick=" not in resp.data

    def test_user_details_has_no_inline_onclick(self, admin_client, user):
        resp = admin_client.get(f"/admin/user/{user.id}")
        assert resp.status_code == 200
        assert b"onclick=" not in resp.data

    def test_profile_has_no_inline_onclick(self, auth_client):
        resp = auth_client.get("/profile/", follow_redirects=True)
        assert resp.status_code == 200
        assert b"onclick=" not in resp.data
