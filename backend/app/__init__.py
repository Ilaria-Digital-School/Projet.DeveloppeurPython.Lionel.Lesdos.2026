"""
Initialisation de l'application Flask.

Ce module crée et configure l'instance de l'application Flask.
"""

import logging
import os
import secrets

# Import relatif des extensions
import sys
import time
from logging.handlers import RotatingFileHandler

from flask import Flask, abort, g, request, session
from flask_cors import CORS
from flask_login import login_required

# Ajouter le répertoire parent au chemin Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Activer Flask-WTF/CSRF
from flask_wtf.csrf import CSRFProtect

# Importer les extensions
from core.extensions import init_extensions

csrf = CSRFProtect()


def create_app(config_name="default"):
    """Crée et configure l'instance de l'application Flask."""
    # Charger les variables d'environnement depuis le fichier .env
    from dotenv import load_dotenv

    load_dotenv()
    # Configuration des chemins - Correction pour éviter les erreurs de résolution
    # Utilisation de os.path.dirname avec __file__ pour obtenir le chemin absolu du répertoire courant
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Remonter au répertoire backend (parent de app)
    backend_dir = os.path.dirname(current_dir)
    # Le répertoire racine est le parent de backend
    root_dir = os.path.dirname(backend_dir)

    # Définir les dossiers de templates et de fichiers statiques avec chemins absolus
    template_folder = os.path.abspath(os.path.join(root_dir, "frontend", "templates"))
    static_folder = os.path.abspath(os.path.join(root_dir, "frontend", "static"))

    # Vérifier que les dossiers existent
    if not os.path.exists(template_folder):
        os.makedirs(template_folder, exist_ok=True, mode=0o755)
    if not os.path.exists(static_folder):
        os.makedirs(static_folder, exist_ok=True, mode=0o755)

    # Création de l'application
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

    # Configuration
    from app.config.config import config

    app.config.from_object(config[config_name])
    if config_name == "production":
        from app.config.config import configurer_redis_production

        configurer_redis_production(app)

    # Derrière le reverse proxy Nginx : restaurer l'IP client réelle et le
    # schéma depuis X-Forwarded-For / X-Forwarded-Proto (1 seul proxy de
    # confiance). Indispensable pour le rate limiting par visiteur et les
    # IP loggées (last_login_ip, appareils).
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    # Configuration du logging
    # Utiliser le répertoire de logs dans le dossier backend
    logs_dir = os.path.join(backend_dir, "logs")
    # S'assurer que le répertoire de logs existe (permissions restrictives)
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True, mode=0o750)

    # Définition du chemin du fichier de log
    log_file = os.path.join(logs_dir, "app.log")

    # Formateur de log détaillé

    # Créer le formateur standard
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Niveau de log depuis la configuration (DEBUG en dev, INFO en prod)
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)

    # Configurer le logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Nettoyer les handlers existants
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Handler pour la console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Handler pour le fichier — rotatif : sans cela le journal grossit
    # indefiniment (11 Mo constates le 19 aout 2026, jamais tourne).
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)

    # Configurer le logger de l'application
    app.logger = root_logger

    # Logs SQLAlchemy : requêtes SQL visibles uniquement en debug
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.setLevel(logging.INFO if app.debug else logging.WARNING)
    sqlalchemy_logger.addHandler(console_handler)
    sqlalchemy_logger.addHandler(file_handler)
    # La racine porte deja ces memes handlers : sans cette ligne,
    # chaque message est enregistre deux fois.
    sqlalchemy_logger.propagate = False

    # Activer les logs pour les requêtes HTTP
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.addHandler(console_handler)
    werkzeug_logger.addHandler(file_handler)
    # La racine porte deja ces memes handlers : sans cette ligne,
    # chaque message est enregistre deux fois.
    werkzeug_logger.propagate = False

    # Désactiver le logging par défaut de Flask-SQLAlchemy pour éviter les doublons
    logging.getLogger("flask_sqlalchemy.engine").setLevel(logging.WARNING)

    # Message de démarrage
    app.logger.info("=" * 80)
    app.logger.info("DÉMARRAGE DE L'APPLICATION")
    app.logger.info(f"Environnement: {config_name.upper()}")
    app.logger.info(f"Répertoire de travail: {os.getcwd()}")
    app.logger.info(f"Répertoire des logs: {os.path.abspath(logs_dir)}")
    app.logger.info(f"Fichier de log: {os.path.abspath(log_file)}")
    app.logger.info("=" * 80)

    # Log des informations de débogage
    app.logger.debug(f"Configuration chargée: {config_name}")
    app.logger.debug(f"Répertoire de travail: {os.getcwd()}")
    app.logger.debug(f"Répertoire des logs: {os.path.abspath(logs_dir)}")
    app.logger.debug(f"Fichier de log: {os.path.abspath(log_file)}")

    # Log de la configuration de la base de données (sans credentials)
    _db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if "@" in _db_uri:
        # Masquer user:password dans l'URI (format: driver://user:pass@host/db)
        _masked_uri = (
            _db_uri.split("://")[0] + "://" + "***:***@" + _db_uri.split("@", 1)[1]
        )
    else:
        _masked_uri = _db_uri
    app.logger.debug(f"Configuration de la base de données: {_masked_uri}")

    app.logger.debug("Base de donnees PostgreSQL configuree.")

    # Middleware pour mesurer le temps de réponse
    @app.before_request
    def before_request():
        g.request_start_time = time.time()
        g.csp_nonce = secrets.token_urlsafe(32)
        if request.method == "POST" and request.path == "/api/auth/login":
            app.logger.info("Tentative de connexion détectée")

        # Prevent session fixation: when the session cookie carries an ID
        # unknown to the store, Flask-Session silently creates a fresh
        # session with a new SID.  Without the marker below the session
        # stays empty and save_session() skips Set-Cookie, leaving the
        # forged value in the browser.  Adding a key makes the session
        # non-empty so the response always overwrites the cookie.
        cookie_name = app.config.get("SESSION_COOKIE_NAME", "session")
        incoming_sid = request.cookies.get(cookie_name)
        if incoming_sid and hasattr(session, "sid") and incoming_sid != session.sid:
            session["_regenerated"] = True

    # Middleware pour logger la réponse
    @app.after_request
    def after_request(response):
        if not hasattr(g, "request_start_time"):
            return response

        # Calcul du temps de réponse
        response_time = (time.time() - g.request_start_time) * 1000  # en millisecondes

        # Log des informations de la requête
        log_data = {
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "response_time": f"{response_time:.2f}ms",
            "remote_addr": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", ""),
        }

        # Ajouter l'utilisateur si authentifié
        if hasattr(g, "user") and g.user:
            log_data["user_id"] = g.user.id
            log_data["user_email"] = getattr(g.user, "email", "inconnu")

        # Formater le log
        log_message = (
            f"{request.method} {request.path} - {response.status_code} "
            f"({response_time:.2f}ms)"
        )

        # Niveau de log en fonction du code de statut
        if 500 <= response.status_code < 600:
            app.logger.error(log_message, extra=log_data)
        elif 400 <= response.status_code < 500:
            app.logger.warning(log_message, extra=log_data)
        else:
            app.logger.info(log_message, extra=log_data)

        # Headers de sécurité (filet de sécurité si Nginx ne les fournit pas)
        # Nginx peut les surcharger ; les définir ici garantit une protection minimale.
        if "X-Content-Type-Options" not in response.headers:
            response.headers["X-Content-Type-Options"] = "nosniff"
        if "X-Frame-Options" not in response.headers:
            response.headers["X-Frame-Options"] = "DENY"
        if "X-XSS-Protection" not in response.headers:
            response.headers["X-XSS-Protection"] = "1; mode=block"
        if "Referrer-Policy" not in response.headers:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        nonce = getattr(g, "csp_nonce", "")
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        if not app.debug and "Strict-Transport-Security" not in response.headers:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response

    # Initialiser toutes les extensions (y compris SQLAlchemy)
    init_extensions(app)

    # Configuration Email autonome et portable
    # Utilise les variables d'environnement uniquement pour être sécurisé
    # Configuration email depuis les variables d'environnement uniquement
    # Note: le chargement depuis la BDD a été supprimé pour des raisons de sécurité
    # (une DB compromise ne doit pas pouvoir rediriger les emails)
    app.config.update(
        {
            # Configuration SMTP OVH
            "MAIL_SERVER": os.environ.get("MAIL_SERVER", "ssl0.ovh.net"),
            "MAIL_PORT": int(os.environ.get("MAIL_PORT", 587)),
            "MAIL_USE_TLS": True,
            "MAIL_USE_SSL": False,
            "MAIL_USERNAME": os.environ.get("MAIL_USERNAME", "contact@example.com"),
            "MAIL_PASSWORD": os.environ.get("MAIL_PASSWORD", ""),
            "MAIL_DEFAULT_SENDER": os.environ.get(
                "MAIL_DEFAULT_SENDER", "Budget App <contact@example.com>"
            ),
            "MAIL_DEBUG": app.debug,
        }
    )

    app.logger.info(
        "📧 Configuration email autonome chargée (SMTP via variables d'environnement)"
    )

    # Configuration et initialisation de CSRF
    app.config["WTF_CSRF_CHECK_DEFAULT"] = True
    _csrf_key = os.environ.get("CSRF_SECRET_KEY")
    if not _csrf_key and not app.debug:
        raise RuntimeError(
            "ERREUR CRITIQUE : La variable d'environnement CSRF_SECRET_KEY n'est pas définie en production. "
            "Elle doit être distincte de SECRET_KEY."
        )
    app.config["WTF_CSRF_SECRET_KEY"] = _csrf_key or app.config.get("SECRET_KEY")

    # Initialiser CSRF
    csrf.init_app(app)

    # Ajouter la fonction csrf_token et le nonce CSP dans le contexte des templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf

        return dict(csrf_token=generate_csrf, csp_nonce=getattr(g, "csp_nonce", ""))

    app.logger.info("CSRF activé avec protection des formulaires")

    # Configuration CORS
    try:
        CORS(
            app,
            resources={
                r"/api/*": {
                    "origins": app.config["CORS_ORIGINS"],
                    "supports_credentials": app.config["CORS_SUPPORTS_CREDENTIALS"],
                    "expose_headers": app.config["CORS_EXPOSE_HEADERS"],
                    "methods": app.config["CORS_METHODS"],
                    "allow_headers": app.config["CORS_ALLOW_HEADERS"],
                }
            },
        )
        app.logger.info("Configuration CORS appliquée avec succès")
    except Exception as e:
        app.logger.error(f"Erreur lors de la configuration CORS: {e}")
        raise

    # Enregistrement des commandes CLI
    from core.commands.account_commands import accounts_cli
    from core.commands.recurring_commands import recurring_cli
    from modules.admin.commands import create_admin

    app.cli.add_command(recurring_cli)
    app.cli.add_command(accounts_cli)
    # « flask create-admin » (documentée dans le README) n'était enregistrée nulle part
    app.cli.add_command(create_admin, "create-admin")

    # Enregistrement des blueprints
    register_blueprints(app)

    # Gestion des erreurs : JSON pour l'API, pages HTML pour le web
    from app.utils.errors import register_error_handlers

    register_error_handlers(app)

    # Route pour servir les images uploadées (authentification requise)
    @app.route("/uploads/<filename>")
    @login_required
    def uploaded_file(filename):
        import re

        from flask import send_from_directory

        # Validation du nom de fichier : lettres, chiffres, underscores, tirets, points uniquement
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", filename) or ".." in filename:
            abort(400)
        upload_folder = os.path.join(app.instance_path, "uploads")
        return send_from_directory(upload_folder, filename)

    return app


def register_blueprints(app):
    """Enregistre les blueprints de l'application."""
    try:
        # Importer les blueprints ici pour éviter les importations circulaires
        app.logger.info("Tentative d'import des blueprints...")

        # Importer le blueprint principal
        from modules.main.main_routes import main_bp

        # Enregistrement du blueprint principal
        app.logger.info(f"Enregistrement du blueprint principal: {main_bp}")
        app.register_blueprint(main_bp)

        # Initialisation du module d'authentification (qui enregistre déjà son propre blueprint)
        app.logger.info("Initialisation du module d'authentification...")
        from modules.auth import init_app as init_auth

        init_auth(app)  # Cette fonction enregistre déjà le blueprint d'authentification

        # Initialisation du module dashboard
        app.logger.info("Initialisation du module dashboard...")
        from modules.dashboard import init_app as init_dashboard

        init_dashboard(app)  # Cette fonction enregistre le blueprint dashboard

        # Blueprints des pages : une erreur d'import arrête le démarrage (sinon
        # l'application tournait sans la page concernée, sans que rien ne
        # le signale à part un message dans les logs)
        from modules.accounts.account_routes import accounts_bp
        from modules.admin.routes import bp as admin_bp
        from modules.budgets import budgets_bp
        from modules.categories.category_routes import categories_bp
        from modules.profile.profile_routes import profile_bp
        from modules.reports import reports_bp
        from modules.transactions.recurring_routes import recurring_bp
        from modules.transactions.transaction_routes import transactions_bp

        for blueprint, prefixe in (
            (accounts_bp, "/comptes"),
            (transactions_bp, "/transactions"),
            (categories_bp, "/categories"),
            (profile_bp, "/profile"),
            (admin_bp, "/admin"),
            (reports_bp, "/reports"),
            (budgets_bp, "/budgets"),
            (recurring_bp, "/transactions"),
        ):
            app.register_blueprint(blueprint, url_prefix=prefixe)

        # API REST v1 (exemptée de CSRF : authentification par session ou JWT)
        from api.v1 import api_v1_bp

        app.register_blueprint(api_v1_bp)
        csrf.exempt(api_v1_bp)
        try:
            from api.v1.auth import auth_limiter

            auth_limiter.init_app(app)
        except Exception as limiter_err:
            app.logger.error(f"Rate limiter auth non initialisé: {limiter_err}")

        app.logger.info(
            f"{len(list(app.url_map.iter_rules()))} routes enregistrées "
            f"({len(app.blueprints)} blueprints)"
        )
        app.logger.info("Blueprints enregistrés avec succès")

    except Exception as e:
        app.logger.error(
            f"Erreur lors de l'enregistrement des blueprints: {e}", exc_info=True
        )
        raise
