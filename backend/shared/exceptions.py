"""
Exceptions personnalisées pour l'application.

Ce module définit des exceptions personnalisées pour gérer les erreurs
de manière plus spécifique et fournir des messages d'erreur plus détaillés.
"""

from flask import jsonify
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    """Classe de base pour les erreurs personnalisées de l'application."""

    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """Convertit l'erreur en dictionnaire pour la sérialisation JSON."""
        rv = dict(self.payload or ())
        rv["message"] = self.message
        rv["status"] = "error"
        rv["code"] = self.status_code
        return rv


class ValidationError(AppError):
    """Exception levée lorsqu'une validation échoue."""

    def __init__(self, message="Erreur de validation", field_errors=None, **kwargs):
        super().__init__(message, **kwargs)
        self.field_errors = field_errors or {}

    def to_dict(self):
        rv = super().to_dict()
        if self.field_errors:
            rv["errors"] = self.field_errors
        return rv


class AuthenticationError(AppError):
    """Exception levée lorsqu'une authentification échoue."""

    status_code = 401

    def __init__(self, message="Authentification requise", **kwargs):
        super().__init__(message, **kwargs)


class ForbiddenError(AppError):
    """Exception levée lorsqu'un utilisateur n'a pas les permissions nécessaires."""

    status_code = 403

    def __init__(self, message="Accès refusé", **kwargs):
        super().__init__(message, **kwargs)


class UnauthorizedError(AppError):
    """Exception levée lorsqu'un utilisateur n'est pas autorisé à effectuer une action."""

    status_code = 401

    def __init__(self, message="Non autorisé", **kwargs):
        super().__init__(message, **kwargs)


class NotFoundError(AppError):
    """Exception levée lorsqu'une ressource n'est pas trouvée."""

    status_code = 404

    def __init__(self, message="Ressource non trouvée", **kwargs):
        super().__init__(message, **kwargs)


class ConflictError(AppError):
    """Exception levée lorsqu'il y a un conflit (ex: doublon)."""

    status_code = 409

    def __init__(self, message="Conflit détecté", **kwargs):
        super().__init__(message, **kwargs)


class ServiceUnavailableError(AppError):
    """Exception levée lorsqu'un service externe n'est pas disponible."""

    status_code = 503

    def __init__(self, message="Service temporairement indisponible", **kwargs):
        super().__init__(message, **kwargs)


# Exceptions spécifiques aux transactions
class InsufficientFundsError(AppError):
    """Exception levée lorsque les fonds sont insuffisants pour une transaction."""

    status_code = 400

    def __init__(self, message="Fonds insuffisants", **kwargs):
        super().__init__(message, **kwargs)


class InvalidTransactionError(AppError):
    """Exception levée lorsqu'une transaction est invalide."""

    status_code = 400

    def __init__(self, message="Transaction invalide", **kwargs):
        super().__init__(message, **kwargs)


class TransactionNotFoundError(NotFoundError):
    """Exception levée lorsqu'une transaction n'est pas trouvée."""

    def __init__(self, message="Transaction non trouvée", **kwargs):
        super().__init__(message, **kwargs)


class AccountNotFoundError(NotFoundError):
    """Exception levée lorsqu'un compte n'est pas trouvé."""

    def __init__(self, message="Compte non trouvé", **kwargs):
        super().__init__(message, **kwargs)


class CategoryNotFoundError(NotFoundError):
    """Exception levée lorsqu'une catégorie n'est pas trouvée."""

    def __init__(self, message="Catégorie non trouvée", **kwargs):
        super().__init__(message, **kwargs)


class DatabaseError(AppError):
    """Exception levée lors d'erreurs de base de données."""

    status_code = 500

    def __init__(self, message="Erreur de base de données", **kwargs):
        super().__init__(message, **kwargs)


def register_error_handlers(app):
    """Enregistre les gestionnaires d'erreurs personnalisés pour l'application.

    Args:
        app: L'instance de l'application Flask
    """

    @app.errorhandler(AppError)
    def handle_app_error(error):
        """Gestionnaire pour les erreurs personnalisées de l'application."""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        """Gestionnaire pour les erreurs 404."""
        if isinstance(error, HTTPException):
            message = error.description
        else:
            message = "La page demandée est introuvable"

        return jsonify({"status": "error", "code": 404, "message": message}), 404

    @app.errorhandler(500)
    def handle_server_error(error):
        """Gestionnaire pour les erreurs 500."""
        app.logger.error(f"Erreur serveur: {str(error)}")

        return (
            jsonify(
                {
                    "status": "error",
                    "code": 500,
                    "message": "Une erreur interne est survenue. Veuillez réessayer plus tard.",
                }
            ),
            500,
        )

    @app.errorhandler(422)
    def handle_validation_error(error):
        """Gestionnaire pour les erreurs de validation (Webargs)."""
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 422,
                    "message": "Erreur de validation",
                    "errors": getattr(error, "messages", None) or {},
                }
            ),
            422,
        )

    @app.errorhandler(429)
    def handle_rate_limit_exceeded(error):
        """Gestionnaire pour les limites de débit dépassées."""
        return (
            jsonify(
                {
                    "status": "error",
                    "code": 429,
                    "message": "Trop de requêtes. Veuillez réessayer plus tard.",
                }
            ),
            429,
        )
