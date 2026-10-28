"""
Utilitaires de sécurité pour la gestion des appareils.

Ce module fournit des fonctions pour la sécurité des appareils, y compris :
- Journalisation des événements de sécurité
- Limitation du taux de requêtes
- Validation des entrées
- Gestion des codes 2FA
- Vérification des appareils
"""

import logging
import os
import secrets
import string
from datetime import datetime, timezone
from functools import wraps

from flask import current_app, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configuration du logger de sécurité
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Le gestionnaire de fichier sera configuré dans init_app()
_handler_configured = False

# Initialisation du rate limiter
device_limiter = None


def init_app(app):
    """Initialise le module de sécurité avec l'application Flask."""
    global device_limiter, _handler_configured

    # Configuration du rate limiter
    device_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=app.config.get("RATELIMIT_STORAGE_URL", "memory://"),
    )
    device_limiter.init_app(app)

    # Configuration du logger de sécurité (une seule fois)
    if not _handler_configured:
        with app.app_context():
            # Création du dossier de logs s'il n'existe pas
            log_dir = os.path.join(app.root_path, "logs")
            os.makedirs(log_dir, exist_ok=True)

            # Configuration du gestionnaire de fichier
            handler = logging.FileHandler(os.path.join(log_dir, "security.log"))
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            )
            security_logger.addHandler(handler)

            _handler_configured = True

    return app


def log_security_event(
    user_id, event_type, ip_address=None, device_id=None, details=None, **kwargs
):
    """
    Journalise un événement de sécurité.

    Args:
        user_id (int): ID de l'utilisateur concerné
        event_type (str): Type d'événement (ex: 'login_attempt', 'device_added')
        ip_address (str, optional): Adresse IP de la requête
        device_id (int, optional): ID de l'appareil concerné
        details (str, optional): Détails supplémentaires sur l'événement
        **kwargs: Champs supplémentaires à inclure dans le journal
    """
    try:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "event_type": event_type,
            "ip_address": ip_address or get_remote_address(),
            "device_id": device_id,
            "details": details or {},
            "user_agent": request.headers.get("User-Agent") if request else None,
        }

        # Ajouter les champs supplémentaires
        log_entry.update(kwargs)

        # Nettoyer les valeurs None
        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        security_logger.info("Security Event: %s", log_entry)

        # Si c'est un événement critique, envoyer une alerte
        if event_type in [
            "suspicious_activity",
            "account_locked",
            "device_compromised",
        ]:
            _send_security_alert(user_id, event_type, log_entry)

    except Exception as e:
        current_app.logger.error(
            f"Erreur lors de la journalisation de l'événement de sécurité: {e}"
        )


def rate_limited(limit_value):
    """
    Décorateur pour limiter le taux de requêtes sur une route.

    Args:
        limit_value (str): Chaîne de limitation (ex: "5 per minute")
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return device_limiter.limit(limit_value)(f)(*args, **kwargs)

        return decorated_function

    return decorator


def validate_device_input(data, required_fields=None):
    """
    Valide les données d'entrée pour un appareil.

    Args:
        data (dict): Données à valider
        required_fields (list, optional): Champs obligatoires

    Returns:
        tuple: (bool, dict) - (is_valid, errors)
    """
    if required_fields is None:
        required_fields = ["name", "device_id", "device_type"]

    errors = {}

    # Vérification des champs obligatoires
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            errors[field] = f"Le champ {field} est obligatoire"

    # Validation des longueurs de champ
    if "name" in data and len(data["name"]) > 100:
        errors["name"] = "Le nom ne peut pas dépasser 100 caractères"

    if "device_id" in data and len(data["device_id"]) > 255:
        errors["device_id"] = "L'ID de l'appareil ne peut pas dépasser 255 caractères"

    # Validation du type d'appareil
    valid_device_types = ["mobile", "tablet", "desktop", "smart_tv", "gaming", "other"]
    if "device_type" in data and data["device_type"] not in valid_device_types:
        errors["device_type"] = (
            f"Type d'appareil invalide. Doit être l'un des suivants: {', '.join(valid_device_types)}"
        )

    # Validation de l'adresse IP si fournie
    if "ip_address" in data and data["ip_address"]:
        try:
            import ipaddress

            ipaddress.ip_address(data["ip_address"])
        except ValueError:
            errors["ip_address"] = "Adresse IP invalide"

    # Validation du user_agent (optionnel mais limité en longueur)
    if "user_agent" in data and data["user_agent"] and len(data["user_agent"]) > 500:
        errors["user_agent"] = "L'user agent est trop long (max 500 caractères)"

    return len(errors) == 0, errors


def generate_2fa_code(length=6):
    """
    Génère un code de vérification aléatoire.

    Args:
        length (int): Longueur du code (par défaut: 6)

    Returns:
        str: Code de vérification
    """
    # Utiliser un générateur sécurisé pour les codes à usage unique
    return "".join(secrets.choice(string.digits) for _ in range(length))


def verify_2fa_code(device, code):
    """
    Vérifie un code de vérification 2FA pour un appareil.

    Args:
        device (Device): L'appareil à vérifier
        code (str): Le code à vérifier

    Returns:
        bool: True si le code est valide, False sinon
    """
    if not device or not code:
        return False

    # Vérifier si le code correspond et n'est pas expiré
    if device.verification_token and device.verification_token_expires:
        is_valid = (
            device.verification_token == code
            and device.verification_token_expires > datetime.now(timezone.utc)
        )

        # Invalider le code après utilisation
        if is_valid:
            device.verification_token = None
            device.verification_token_expires = None

            from core.extensions import db

            db.session.commit()

        return is_valid

    return False


def _send_security_alert(user_id, event_type, event_data):
    """
    Envoie une alerte de sécurité (par email, notification push, etc.)

    Args:
        user_id (int): ID de l'utilisateur
        event_type (str): Type d'événement
        event_data (dict): Données de l'événement
    """
    # Implémentation basique - à étendre selon les besoins
    subject = f"Alerte de sécurité: {event_type}"
    message = f"Événement de sécurité détecté: {event_type}\n\nDétails:\n{event_data}"

    # Ici, vous pourriez envoyer un email, une notification push, etc.
    current_app.logger.warning(f"ALERTE DE SÉCURITÉ - {subject}\n{message}")

    # Exemple d'envoi d'email (nécessite la configuration de Flask-Mail)
    try:
        from flask_mail import Message

        from core.extensions import db, mail

        # Récupérer l'utilisateur depuis la base de données
        from core.models.user import User

        user = db.session.get(User, user_id)

        if user and user.email:
            msg = Message(
                subject=subject,
                recipients=[user.email],
                body=message,
                sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
            )
            mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'envoi de l'alerte de sécurité: {e}")


def check_request_rate_limit(identifier, limit, period):
    """
    Vérifie si une requête dépasse la limite de taux.

    Args:
        identifier (str): Identifiant unique pour la limitation
        limit (int): Nombre maximum de requêtes
        period (int): Période en secondes

    Returns:
        tuple: (is_allowed, headers) - (bool, dict)
    """
    return device_limiter.check(f"{identifier}:{limit}:{period}")


def get_client_ip():
    """
    Récupère l'adresse IP du client en tenant compte des proxies.

    Returns:
        str: Adresse IP du client
    """
    # Liste des en-têtes à vérifier pour l'IP réelle (en cas de proxy)
    ip_headers = [
        "X-Forwarded-For",
        "X-Real-IP",
        "X-Client-IP",
        "X-Forwarded",
        "Forwarded-For",
        "X-Cluster-Client-Ip",
        "Proxy-Client-IP",
        "WL-Proxy-Client-IP",
        "HTTP_X_FORWARDED_FOR",
        "HTTP_X_FORWARDED",
        "HTTP_X_CLUSTER_CLIENT_IP",
        "HTTP_CLIENT_IP",
        "HTTP_FORWARDED_FOR",
        "HTTP_FORWARDED",
        "HTTP_VIA",
        "REMOTE_ADDR",
    ]

    for header in ip_headers:
        ip = request.headers.get(header, "").split(",")[0].strip()
        if ip:
            return ip

    # IP de repli si remote_addr absent (valeur, pas un bind socket)
    return request.remote_addr or "0.0.0.0"  # nosec B104
