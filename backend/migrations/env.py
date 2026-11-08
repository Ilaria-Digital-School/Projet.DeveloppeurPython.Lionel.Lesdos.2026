import logging
from logging.config import fileConfig

from alembic import context
from flask import current_app
from sqlalchemy import create_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions["migrate"].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions["migrate"].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
    except AttributeError:
        return str(get_engine().url).replace("%", "%%")


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option("sqlalchemy.url", get_engine_url())
target_db = current_app.extensions["migrate"].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# Import des modèles depuis le bon chemin
try:
    from core import extensions
    from core.models.account import Account
    from core.models.budget import Budget
    from core.models.budget_history import BudgetHistory
    from core.models.category import Category
    from core.models.device import Device
    from core.models.notification import Notification
    from core.models.notification_preference import NotificationPreference
    from core.models.permission import Permission
    from core.models.report import Report
    from core.models.role import Role
    from core.models.security_event import SecurityEvent
    from core.models.session import UserSession
    from core.models.setting import UserSetting
    from core.models.token_blacklist import TokenBlacklist
    from core.models.transactions import Transaction
    from core.models.user import User

    target_metadata = extensions.db.Model.metadata
except ImportError as exc:
    # Surtout pas de repli sur target_metadata = None : l'autogenerate
    # comparerait alors la base a un registre vide et proposerait de
    # supprimer toutes les tables. Une commande qui echoue vaut mieux
    # qu'une migration silencieusement fausse.
    raise RuntimeError(
        "Import des modeles impossible : l'autogenerate Alembic serait "
        "aveugle. Corrigez l'import avant de relancer une commande de "
        "migration."
    ) from exc


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    conf_args = current_app.extensions["migrate"].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"), poolclass=None
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
