from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from .auth_service import auth_service


def has_permission(permission_name):
    """Décorateur pour vérifier si l'utilisateur a la permission requise."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            current_user = get_jwt_identity()
            if not current_user:
                return jsonify({"error": "Non authentifié"}), 401

            if not auth_service.has_permission(current_user, permission_name):
                return jsonify({"error": "Permission refusée"}), 403

            return f(*args, **kwargs)

        return wrapper

    return decorator
