"""
Gestion centralisée des erreurs de l'application.

Ce module fournit des fonctions pour gérer les erreurs HTTP courantes
et les exceptions personnalisées.
"""

from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException


# Classes d'exception personnalisées
class ValidationError(Exception):
    """Exception levée lors d'erreurs de validation des données."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class NotFoundError(Exception):
    """Exception levée lorsqu'une ressource n'est pas trouvée."""

    def __init__(self, message, resource_type=None, resource_id=None):
        super().__init__(message)
        self.message = message
        self.resource_type = resource_type
        self.resource_id = resource_id


class UnauthorizedError(Exception):
    """Exception levée lors d'erreurs d'autorisation."""

    def __init__(self, message, user_id=None, required_permission=None):
        super().__init__(message)
        self.message = message
        self.user_id = user_id
        self.required_permission = required_permission


class ConflictError(Exception):
    """Exception levée lors de conflits de données ou d'état."""

    def __init__(self, message, resource_type=None, conflict_reason=None):
        super().__init__(message)
        self.message = message
        self.resource_type = resource_type
        self.conflict_reason = conflict_reason


class DatabaseError(Exception):
    """Exception levée lors d'erreurs de base de données."""

    def __init__(self, message, operation=None, table=None):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.table = table


class APIError(Exception):
    """Exception levée lors d'erreurs d'API."""

    def __init__(self, message, status_code=500, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload


# Fonctions de gestion d'erreurs
def handle_api_error(error):
    """Gère les erreurs d'API et retourne une réponse JSON appropriée."""
    if isinstance(error, APIError):
        response = {
            "error": "API Error",
            "code": error.status_code,
            "message": error.message,
        }
        if error.payload:
            response.update(error.payload)
        return jsonify(response), error.status_code

    # Pour les autres types d'erreurs - ne pas exposer les détails
    from flask import current_app

    if current_app.debug:
        message = str(error)
    else:
        message = "Une erreur interne est survenue."
    return (
        jsonify({"error": "Internal Server Error", "code": 500, "message": message}),
        500,
    )


def handle_validation_error(error):
    """Gère les erreurs de validation."""
    if isinstance(error, ValidationError):
        return (
            jsonify(
                {
                    "error": "Validation Error",
                    "code": 400,
                    "message": error.message,
                    "field": error.field,
                }
            ),
            400,
        )
    return handle_api_error(error)


def handle_not_found_error(error):
    """Gère les erreurs de ressource non trouvée."""
    if isinstance(error, NotFoundError):
        return (
            jsonify(
                {
                    "error": "Not Found",
                    "code": 404,
                    "message": error.message,
                    "resource_type": error.resource_type,
                    "resource_id": error.resource_id,
                }
            ),
            404,
        )
    return handle_api_error(error)


def handle_unauthorized_error(error):
    """Gère les erreurs d'autorisation."""
    if isinstance(error, UnauthorizedError):
        return (
            jsonify(
                {
                    "error": "Unauthorized",
                    "code": 401,
                    "message": error.message,
                    "user_id": error.user_id,
                    "required_permission": error.required_permission,
                }
            ),
            401,
        )
    return handle_api_error(error)


def handle_database_error(error):
    """Gère les erreurs de base de données."""
    if isinstance(error, DatabaseError):
        return (
            jsonify(
                {
                    "error": "Database Error",
                    "code": 500,
                    "message": error.message,
                    "operation": error.operation,
                    "table": error.table,
                }
            ),
            500,
        )
    return handle_api_error(error)


def handle_conflict_error(error):
    """Gère les erreurs de conflit."""
    if isinstance(error, ConflictError):
        return (
            jsonify(
                {
                    "error": "Conflict",
                    "code": 409,
                    "message": error.message,
                    "resource_type": error.resource_type,
                    "conflict_reason": error.conflict_reason,
                }
            ),
            409,
        )
    return handle_api_error(error)


def register_error_handlers(app):
    """Enregistre les gestionnaires d'erreurs pour l'application."""

    @app.errorhandler(400)
    def bad_request_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": "Bad Request",
                        "code": 400,
                        "message": str(error) or "La requête est incorrecte.",
                    }
                ),
                400,
            )
        return render_template("errors/400.html", error=error), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "code": 401,
                        "message": "Authentification requise.",
                    }
                ),
                401,
            )
        return render_template("errors/401.html", error=error), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": "Forbidden",
                        "code": 403,
                        "message": "Vous n'avez pas la permission d'accéder à cette ressource.",
                    }
                ),
                403,
            )
        return render_template("errors/403.html", error=error), 403

    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": "Not Found",
                        "code": 404,
                        "message": "La ressource demandée est introuvable.",
                    }
                ),
                404,
            )
        return render_template("errors/404.html", error=error), 404

    @app.errorhandler(413)
    def request_entity_too_large_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": "Request Entity Too Large",
                        "code": 413,
                        "message": "Le fichier est trop volumineux.",
                    }
                ),
                413,
            )
        return render_template("errors/413.html", error=error), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": "Internal Server Error",
                        "code": 500,
                        "message": "Une erreur interne est survenue.",
                    }
                ),
                500,
            )

        # En mode debug, on affiche plus de détails
        if app.debug:
            return render_template("errors/500_debug.html", error=error), 500
        return render_template("errors/500.html", error=error), 500

    # Gestion des erreurs HTTP génériques
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": error.name,
                        "code": error.code,
                        "message": error.description,
                    }
                ),
                error.code,
            )
        return render_template("errors/generic.html", error=error), error.code

    # Gestion des exceptions non gérées
    @app.errorhandler(Exception)
    def handle_exception(error):
        # Log l'erreur
        app.logger.error(f"Erreur non gérée: {str(error)}", exc_info=True)

        if request.is_json or request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": "Internal Server Error",
                        "code": 500,
                        "message": "Une erreur inattendue est survenue.",
                    }
                ),
                500,
            )

        # En mode debug, on affiche plus de détails
        if app.debug:
            return render_template("errors/500_debug.html", error=error), 500
        return render_template("errors/500.html", error=error), 500
