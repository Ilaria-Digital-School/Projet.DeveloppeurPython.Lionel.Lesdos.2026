"""
Configuration de base de l'application.
"""

import os
from datetime import timedelta


class Config:
    """Configuration de base de l'application."""

    # Clé secrète pour la sécurité (obligatoire via variable d'environnement)
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "ERREUR CRITIQUE : La variable d'environnement SECRET_KEY n'est pas définie. "
            "Définissez-la avec : export SECRET_KEY='votre-cle-secrete-longue-et-aleatoire'"
        )

    # Configuration des chemins
    config_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(os.path.dirname(config_dir))
    instance_dir = os.path.join(backend_dir, "instance")
    os.makedirs(instance_dir, exist_ok=True, mode=0o750)

    # Configuration de la base de données PostgreSQL (obligatoire via variable d'environnement)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    # Compatibilité : certains PaaS (Heroku) fournissent postgres:// que SQLAlchemy 2.x refuse
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    if not SQLALCHEMY_DATABASE_URI:
        raise RuntimeError(
            "ERREUR CRITIQUE : La variable d'environnement DATABASE_URL n'est pas définie. "
            "Définissez-la avec : export DATABASE_URL='postgresql://user:pass@localhost:5432/budget'"
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Configuration de la session
    SESSION_TYPE = "cachelib"
    _session_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "instance",
        "sessions",
    )
    os.makedirs(_session_dir, exist_ok=True)
    from cachelib.file import FileSystemCache

    SESSION_CACHELIB = FileSystemCache(cache_dir=_session_dir, threshold=500)
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() in [
        "true",
        "on",
        "1",
    ]
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Configuration de sécurité
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT")
    if not SECURITY_PASSWORD_SALT:
        raise RuntimeError(
            "ERREUR CRITIQUE : La variable d'environnement SECURITY_PASSWORD_SALT n'est pas définie."
        )
    SECURITY_PASSWORD_HASH = "bcrypt"
    SECURITY_CONFIRMABLE = True
    SECURITY_RECOVERABLE = True
    SECURITY_TRACKABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_SEND_REGISTER_EMAIL = False  # Désactivé en développement

    # Configuration des emails OVH
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.example.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ["true", "on", "1"]
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "contact@example.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "Budget App <contact@example.com>"
    )

    # Configuration CORS
    _cors_env = os.environ.get("CORS_ORIGINS")
    CORS_ORIGINS = (
        [o.strip() for o in _cors_env.split(",") if o.strip()] if _cors_env else []
    )
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_EXPOSE_HEADERS = ["Content-Type", "X-CSRFToken"]
    CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS = ["Content-Type", "X-CSRFToken", "Authorization"]

    # Configuration JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "ERREUR CRITIQUE : La variable d'environnement JWT_SECRET_KEY n'est pas définie."
        )
    # Durées de vie des tokens (en secondes, surchargeables via l'environnement)
    _jwt_access_env = (
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", "").split("#")[0].strip()
    )
    _jwt_refresh_env = (
        os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", "").split("#")[0].strip()
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(_jwt_access_env) if _jwt_access_env else 3600
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(_jwt_refresh_env) if _jwt_refresh_env else 604800
    )
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_COOKIE_SECURE = os.environ.get("JWT_COOKIE_SECURE", "true").lower() in [
        "true",
        "on",
        "1",
    ]
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True

    # Configuration du taux limite
    RATELIMIT_DEFAULT = "2000 per day;500 per hour"
    RATELIMIT_STORAGE_URI = os.environ.get(
        "RATELIMIT_STORAGE_URL", os.environ.get("REDIS_URL", "redis://redis:6379/1")
    )
    RATELIMIT_STORAGE_URL = RATELIMIT_STORAGE_URI  # Alias pour compatibilité
    RATELIMIT_STRATEGY = "fixed-window"

    # Configuration du cache
    CACHE_TYPE = "flask_caching.backends.SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300

    # Configuration Redis / RQ (file de tâches)
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    QUEUE_NAME = os.environ.get("QUEUE_NAME", "default")

    # Configuration du débogage
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    # Configuration des logs
    LOG_LEVEL = "DEBUG"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DIR = os.path.join(backend_dir, "logs")

    # Créer le répertoire de logs s'il n'existe pas (permissions restrictives)
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True, mode=0o750)

    LOG_FILE = os.path.join(LOG_DIR, "app.log")

    # Configuration de la pagination
    ITEMS_PER_PAGE = 20

    # Configuration des uploads
    UPLOAD_FOLDER = os.path.join(instance_dir, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}

    # Créer le répertoire d'upload s'il n'existe pas
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True, mode=0o750)

    # Configuration du fuseau horaire
    TIMEZONE = "Europe/Paris"

    # Configuration des tests
    TESTING = False
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    """Configuration pour l'environnement de développement."""

    DEBUG = True
    SQLALCHEMY_ECHO = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get("WTF_CSRF_SECRET_KEY")
    if not WTF_CSRF_SECRET_KEY:
        raise RuntimeError(
            "ERREUR CRITIQUE : La variable d'environnement WTF_CSRF_SECRET_KEY n'est pas définie."
        )


class TestingConfig(Config):
    """Configuration pour les tests."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL_TEST",
        "postgresql://budget_user:password@localhost:5432/budget_test",
    )
    WTF_CSRF_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_STORAGE_URL = "memory://"


class ProductionConfig(Config):
    """Configuration pour la production."""

    DEBUG = False
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SAMESITE = "Strict"
    LOG_LEVEL = "INFO"
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "https://example.com").split(",")
        if o.strip()
    ]

    # Sessions Redis en production (au lieu de FileSystemCache) ; la connexion
    # (SESSION_REDIS) est créée par configurer_redis_production au démarrage
    SESSION_TYPE = "redis"


def configurer_redis_production(app):
    """Connexion Redis des sessions, exigée en production.

    Faite au démarrage de l'app en production, et non dans le corps de
    ProductionConfig : ce dernier s'exécute à l'import du module et exigeait
    REDIS_URL partout (tests, développement, outils).
    """
    import redis

    url = os.environ.get("REDIS_URL")
    if not url:
        raise RuntimeError(
            "ERREUR CRITIQUE : La variable d'environnement REDIS_URL n'est pas définie en production."
        )
    app.config["SESSION_REDIS"] = redis.from_url(url)


# Dictionnaire des configurations disponibles
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
