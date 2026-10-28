"""
API REST v1 — Gestion des utilisateurs.

Routes:
    PUT    /api/v1/users/<id>/profile     Mettre à jour le profil
    GET    /api/v1/users/<id>/roles       Récupérer les rôles
    POST   /api/v1/users/<id>/roles/<rid> Ajouter un rôle
    DELETE /api/v1/users/<id>/roles/<rid> Supprimer un rôle
    PUT    /api/v1/users/<id>             Mettre à jour un utilisateur
    DELETE /api/v1/users/<id>             Supprimer un utilisateur
"""

import logging

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from core.extensions import db
from core.services.user import UserService

from . import api_v1_bp
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


def _has_permission(permission):
    """Vérifie si l'utilisateur courant (JWT) a la permission donnée.

    Retourne True si l'utilisateur possède la permission nommée via ses
    rôles, ou s'il a le rôle admin.
    """
    from core.models.user import User

    user_id = get_jwt_identity()
    if not user_id:
        return False

    user = db.session.get(User, int(user_id))
    if user is None:
        return False

    return user.has_permission(permission) or user.has_role("admin")


@api_v1_bp.route("/users/<int:user_id>/profile", methods=["PUT"])
@jwt_required()
def v1_update_user_profile(user_id):
    """Met à jour le profil d'un utilisateur."""
    current_user_id = get_jwt_identity()
    if user_id != int(current_user_id) and not _has_permission("update:users"):
        return api_error("Acces non autorise", 403)

    try:
        data = request.get_json()
        if not data:
            return api_error("Aucune donnée fournie", 400)

        service = UserService(current_app)
        user = service.update_user_profile(user_id, data)

        if not user:
            return api_error(f"Utilisateur avec l'ID {user_id} non trouvé", 404)

        return api_success(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": getattr(user, "first_name", ""),
                    "last_name": getattr(user, "last_name", ""),
                },
            },
            message="Profil mis à jour avec succès",
        )

    except Exception as e:
        logger.error(f"Erreur mise à jour profil: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/users/<int:user_id>/roles", methods=["GET"])
@jwt_required()
def v1_get_user_roles(user_id):
    """Récupère les rôles d'un utilisateur."""
    current_user_id = get_jwt_identity()

    if user_id != int(current_user_id) and not _has_permission("read:users"):
        return api_error("Accès non autorisé", 403)

    try:
        user = UserService.get_user_by_id(user_id)
        if not user:
            return api_error("Utilisateur non trouvé", 404)

        roles = (
            [{"id": r.id, "name": r.name} for r in user.roles]
            if hasattr(user, "roles")
            else []
        )
        return api_success(
            {
                "user_id": user.id,
                "roles": roles,
            }
        )

    except Exception as e:
        logger.error(f"Erreur récupération rôles: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/users/<int:user_id>/roles/<int:role_id>", methods=["POST"])
@jwt_required()
def v1_add_user_role(user_id, role_id):
    """Ajoute un rôle à un utilisateur.

    La gestion des rôles exige toujours la permission update:users,
    y compris sur son propre compte (sinon escalade de privilèges).
    """
    if not _has_permission("update:users"):
        return api_error("Accès non autorisé", 403)

    try:
        user = UserService.add_role_to_user(user_id, role_id)
        if not user:
            return api_error("Utilisateur non trouvé", 404)

        return api_success(message="Rôle ajouté avec succès")

    except Exception as e:
        logger.error(f"Erreur ajout rôle: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/users/<int:user_id>/roles/<int:role_id>", methods=["DELETE"])
@jwt_required()
def v1_remove_user_role(user_id, role_id):
    """Supprime un rôle d'un utilisateur.

    La gestion des rôles exige toujours la permission update:users,
    y compris sur son propre compte.
    """
    if not _has_permission("update:users"):
        return api_error("Accès non autorisé", 403)

    try:
        user = UserService.remove_role_from_user(user_id, role_id)
        if not user:
            return api_error("Utilisateur non trouvé", 404)

        return api_success(message="Rôle supprimé avec succès")

    except Exception as e:
        logger.error(f"Erreur suppression rôle: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
def v1_update_user(user_id):
    """Met à jour les informations d'un utilisateur."""
    current_user_id = get_jwt_identity()

    if user_id != int(current_user_id) and not _has_permission("update:users"):
        return api_error("Accès non autorisé", 403)

    data = request.get_json()
    if not data:
        return api_error("Aucune donnée fournie", 400)

    try:
        service = UserService(current_app)
        user = service.update_user_profile(user_id, data)
        if not user:
            return api_error("Utilisateur non trouvé", 404)

        return api_success(message="Utilisateur mis à jour avec succès")

    except Exception as e:
        logger.error(f"Erreur mise à jour utilisateur: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def v1_delete_user(user_id):
    """Supprime (désactive) un utilisateur."""
    current_user_id = get_jwt_identity()

    if user_id == int(current_user_id):
        return api_error("Vous ne pouvez pas supprimer votre propre compte", 403)

    if not _has_permission("delete:users"):
        return api_error("Accès non autorisé", 403)

    try:
        service = UserService(current_app)
        success = service.deactivate_user(
            user_id, reason="Supprimé par un administrateur"
        )
        if not success:
            return api_error("Utilisateur non trouvé", 404)

        return api_success(message="Utilisateur désactivé avec succès")

    except Exception as e:
        logger.error(f"Erreur suppression utilisateur: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
