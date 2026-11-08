"""
Décorateurs pour l'autorisation et la gestion des permissions
"""

from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(f):
    """
    Décorateur pour restreindre l'accès aux administrateurs uniquement.

    Usage:
    @admin_required
    def my_admin_function():
        pass
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Vérifier que l'utilisateur est connecté
        if not current_user.is_authenticated:
            abort(401)  # Non authentifié

        # Vérifier que l'utilisateur a le rôle admin
        if not has_admin_role(current_user):
            abort(403)  # Accès refusé

        return f(*args, **kwargs)

    return decorated_function


def has_admin_role(user):
    """
    Vérifie si un utilisateur a le rôle administrateur.

    Args:
        user: Instance de User

    Returns:
        bool: True si l'utilisateur est admin, False sinon
    """
    if not user:
        return False

    # Vérifier si l'utilisateur a le rôle 'admin'
    for role in user.roles:
        if role.name == "admin":
            return True
    return False
