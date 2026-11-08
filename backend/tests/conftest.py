"""
Fixtures globales pour la suite de tests pytest.

IMPORTANT : Les variables d'environnement sont définies AVANT tout import applicatif
car config.py les évalue au moment de l'import des classes Config.
"""

import os

# === Variables d'environnement AVANT tout import applicatif ===
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("SECURITY_PASSWORD_SALT", "test-salt-for-pytest")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-pytest-only-32b-min")
os.environ.setdefault("WTF_CSRF_SECRET_KEY", "test-csrf-secret-for-pytest")
os.environ.setdefault("CSRF_SECRET_KEY", "test-csrf-secret-for-pytest")
os.environ.setdefault(
    "DATABASE_URL", "postgresql://budget_user:password@localhost:5432/budget_test"
)

import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

# Ajouter le répertoire backend au PYTHONPATH
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from core.extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Crée l'application Flask en mode testing (scope=session)."""
    app = create_app("testing")
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": os.environ.get(
                "DATABASE_URL_TEST",
                "postgresql://budget_user:password@localhost:5432/budget_test",
            ),
            "WTF_CSRF_ENABLED": False,
            "SERVER_NAME": "localhost",
            "PREFERRED_URL_SCHEME": "http",
            "LOGIN_DISABLED": False,
            "SESSION_PROTECTION": None,
        }
    )
    # === GARDE-FOU CRITIQUE ===
    # Les tests VIDENT toutes les tables après chaque test et les SUPPRIMENT
    # en fin de session (drop_all). Refuser toute base dont le nom ne
    # contient pas "test" pour empêcher la destruction de la production.
    # (Incident du 05/07/2026 : pytest lancé sur la base 'budget' de prod.)
    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    db_name = db_uri.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in db_name.lower():
        pytest.exit(
            f"SÉCURITÉ : refus de lancer les tests sur la base '{db_name}'. "
            "Les tests détruisent la base cible (drop_all). "
            "Utilisez une base dont le nom contient 'test' "
            "(ex: DATABASE_URL_TEST=...:5432/budget_test).",
            returncode=1,
        )

    # Désactiver la protection de session pour les tests
    from core.extensions import login_manager

    login_manager.session_protection = None
    yield app


@pytest.fixture(scope="session")
def _db_create(app):
    """Crée les tables une fois pour toute la session."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture(autouse=True)
def db_session(app, _db_create):
    """Fournit une session DB isolée par test via rollback."""
    with app.app_context():
        yield _db_create.session
        _db_create.session.rollback()
        # Nettoyer toutes les tables après chaque test
        for table in reversed(_db_create.metadata.sorted_tables):
            _db_create.session.execute(table.delete())
        _db_create.session.commit()


@pytest.fixture
def client(app):
    """Fournit un client de test Flask.

    db_session garde un contexte d'application ouvert pendant tout le test : le
    client le réutilise, donc le même `g` d'une requête à l'autre. Flask-Login y
    met en cache l'utilisateur courant (g._login_user) : sans le vider, la
    requête suivante voyait l'utilisateur de la précédente (connexion,
    déconnexion ou Bearer JWT ignorés), contrairement à un vrai serveur.
    """
    from flask import g

    client = app.test_client()
    ouvrir = client.open

    def open_avec_g_neuf(*args, **kwargs):
        g.pop("_login_user", None)
        return ouvrir(*args, **kwargs)

    client.open = open_avec_g_neuf
    return client


@pytest.fixture
def user(app, db_session):
    """Crée un utilisateur de test standard."""
    from core.models.user import User

    u = User(
        username="testuser",
        email="test@example.com",
        is_active=True,
        email_verified=True,
    )
    u.password = "TestPassword123!"
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def admin_user(app, db_session):
    """Crée un utilisateur admin de test."""
    from core.models.role import Role
    from core.models.user import User

    # Créer le rôle admin s'il n'existe pas
    admin_role = db_session.query(Role).filter_by(name="admin").first()
    if not admin_role:
        admin_role = Role(name="admin", description="Administrateur")
        db_session.add(admin_role)
        db_session.flush()

    u = User(
        username="adminuser",
        email="admin@example.com",
        is_active=True,
        email_verified=True,
    )
    u.password = "AdminPassword123!"
    u.roles.append(admin_role)
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def auth_client(app, client, user, db_session):
    """Client de test authentifié via session (login web)."""
    with client.session_transaction() as sess:
        sess["_user_id"] = user.get_id()
        sess["_fresh"] = True
    return client


@pytest.fixture
def admin_client(app, client, admin_user, db_session):
    """Client de test authentifié en tant qu'admin via session (login web)."""
    with client.session_transaction() as sess:
        sess["_user_id"] = admin_user.get_id()
        sess["_fresh"] = True
    return client


@pytest.fixture
def auth_headers(app, user):
    """Headers JWT pour les tests d'API."""
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(identity=user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def account(app, db_session, user):
    """Crée un compte bancaire de test."""
    from core.models.account import Account

    acc = Account(
        user_id=user.id,
        name="Compte Courant Test",
        account_type="courant",
        balance=Decimal("1500.00"),
        currency="EUR",
    )
    db_session.add(acc)
    db_session.flush()
    return acc


@pytest.fixture
def category(app, db_session, user):
    """Crée une catégorie de dépense de test."""
    from core.models.category import Category

    cat = Category(
        user_id=user.id,
        name="Alimentation",
        description="Courses alimentaires",
        color="#FF5733",
        icon="fa-shopping-cart",
        is_expense=True,
        category_type="expense",
    )
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture
def income_category(app, db_session, user):
    """Crée une catégorie de revenu de test."""
    from core.models.category import Category

    cat = Category(
        user_id=user.id,
        name="Salaire",
        description="Revenus salariaux",
        color="#28A745",
        icon="fa-money-bill",
        is_expense=False,
        category_type="income",
    )
    db_session.add(cat)
    db_session.flush()
    return cat


@pytest.fixture
def transaction(app, db_session, user, account, category):
    """Crée une transaction de test."""
    from core.models.transactions import Transaction

    t = Transaction(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id,
        montant=Decimal("42.50"),
        type_transaction="achat",
        libelle="Courses Carrefour",
        date_heure_transaction=datetime.now(timezone.utc),
        statut="comptabilise",
        devise="EUR",
    )
    db_session.add(t)
    db_session.flush()
    return t


@pytest.fixture
def budget(app, db_session, user, category):
    """Crée un budget de test."""
    from core.models.budget import Budget

    b = Budget(
        user_id=user.id,
        category_id=category.id,
        amount=Decimal("500.00"),
        period="monthly",
        start_date=date.today().replace(day=1),
        end_date=date.today().replace(day=28),
    )
    db_session.add(b)
    db_session.flush()
    return b
