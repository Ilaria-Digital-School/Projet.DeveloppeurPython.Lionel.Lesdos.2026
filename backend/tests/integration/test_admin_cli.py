"""Commande « flask create-admin » (installation, cf. README)."""

import pytest

pytestmark = pytest.mark.integration


def test_create_admin_cree_un_administrateur(app):
    from core.models.user import User

    res = app.test_cli_runner().invoke(
        args=[
            "create-admin",
            "--email",
            "chef@example.test",
            "--username",
            "chef",
            "--password",
            "Admin-Test-2026!",
        ]
    )
    assert res.exit_code == 0, res.output
    admin = User.query.filter_by(email="chef@example.test").one()
    assert admin.is_admin
    assert admin.check_password("Admin-Test-2026!")
