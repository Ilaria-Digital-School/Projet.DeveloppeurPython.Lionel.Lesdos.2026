"""
API REST v1 — Catégories.

Routes:
    GET    /api/v1/categories          Liste des catégories
    POST   /api/v1/categories          Créer une catégorie
    GET    /api/v1/categories/<id>     Détail d'une catégorie
    PUT    /api/v1/categories/<id>     Modifier une catégorie
    DELETE /api/v1/categories/<id>     Supprimer une catégorie
"""

import logging

from flask import request
from flask_login import current_user, login_required

from core.extensions import db
from core.models.category import Category
from core.services.categories.category_services import CategoryService
from core.services.categories.exceptions import (
    CategoryIntegrityError,
    CategoryNotFoundError,
    CategoryPermissionError,
    CategoryValidationError,
)

from . import api_v1_bp
from .auth import auth_limiter
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


# ── LIST / CREATE ────────────────────────────────────────────────────────────


@api_v1_bp.route("/categories", methods=["GET"])
@login_required
def list_categories():
    """Retourne les catégories de l'utilisateur courant."""
    try:
        user_id = current_user.id
        # Uniquement les catégories personnelles : les modèles globaux
        # (user_id NULL) servent de gabarits copiés à l'inscription
        categories = (
            Category.query.filter(Category.user_id == user_id)
            .order_by(Category.name)
            .all()
        )

        categories_data = []
        for cat in categories:
            if hasattr(cat, "category_type") and cat.category_type:
                category_type = cat.category_type
            elif cat.is_expense:
                category_type = "expense"
            else:
                category_type = "income"

            categories_data.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description or "",
                    "type": category_type,
                    "color": cat.color or "#6c757d",
                    "icon": cat.icon or "folder",
                    "is_default": cat.is_default,
                    "created_at": (
                        cat.created_at.isoformat() if cat.created_at else None
                    ),
                }
            )

        return api_success({"categories": categories_data})

    except Exception as e:
        logger.error(f"Erreur liste catégories: {e}", exc_info=True)
        return api_error("Erreur lors du chargement des catégories", 500)


@api_v1_bp.route("/categories", methods=["POST"])
@login_required
@auth_limiter.limit("20 per minute")
def create_category():
    """Crée une nouvelle catégorie."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Données JSON requises", 400)

        name = (data.get("name") or "").strip()
        if not name:
            return api_error("Nom de la catégorie requis", 400)

        description = (data.get("description") or "").strip() or None
        color = (data.get("color") or "#4caf50").strip()
        category_type = (data.get("type") or "expense").strip()

        if category_type == "transfer":
            icon = (data.get("icon") or "exchange-alt").strip()
            is_expense = True
        else:
            icon = (data.get("icon") or "tag").strip()
            is_expense = category_type != "income"

        category = CategoryService.create_category(
            name=name,
            is_expense=is_expense,
            user_id=current_user.id,
            description=description,
            color=color,
            icon=icon,
            category_type=category_type,
        )

        response_type = category_type
        if category_type == "transfer":
            response_type = "transfer"
        elif not category.is_expense:
            response_type = "income"
        elif category.is_expense:
            response_type = "expense"

        return api_success(
            {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "color": category.color,
                "icon": category.icon,
                "type": response_type,
                "is_income": not category.is_expense,
                "transaction_count": 0,
            },
            status_code=201,
        )

    except CategoryIntegrityError as e:
        db.session.rollback()
        return api_error(str(e), 409)
    except CategoryValidationError as e:
        db.session.rollback()
        return api_error(str(e), 400)
    except Exception as e:
        logger.error(f"Erreur création catégorie: {e}", exc_info=True)
        db.session.rollback()
        return api_error("Erreur lors de la création de la catégorie", 500)


# ── DETAIL / UPDATE / DELETE ─────────────────────────────────────────────────


@api_v1_bp.route("/categories/<int:category_id>", methods=["GET"])
@login_required
def get_category(category_id):
    """Retourne le détail d'une catégorie."""
    try:
        category = CategoryService.get_category(
            category_id=category_id,
            user_id=current_user.id,
            with_transactions=False,
        )

        response_type = category.category_type or (
            "expense" if category.is_expense else "income"
        )

        return api_success(
            {
                "id": category.id,
                "name": category.name,
                "description": category.description or "",
                "type": response_type,
                "color": category.color or "#6c757d",
                "icon": category.icon or "folder",
                "is_default": getattr(category, "is_global", False),
                "created_at": (
                    category.created_at.isoformat()
                    if hasattr(category, "created_at") and category.created_at
                    else None
                ),
            }
        )

    except CategoryNotFoundError:
        return api_error("Catégorie introuvable", 404)
    except CategoryPermissionError:
        return api_error("Accès non autorisé", 403)
    except Exception as e:
        logger.error(f"Erreur récupération catégorie {category_id}: {e}", exc_info=True)
        return api_error("Erreur lors du chargement de la catégorie", 500)


@api_v1_bp.route("/categories/<int:category_id>", methods=["PUT"])
@login_required
def update_category(category_id):
    """Met à jour une catégorie."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Données JSON requises", 400)

        category_type = (data.get("type") or "expense").strip()
        name = (data.get("name") or "").strip()
        if not name:
            return api_error("Le nom de la catégorie est requis", 400)

        if category_type == "transfer":
            icon = (data.get("icon") or "exchange-alt").strip()
            is_expense = True
        else:
            icon = (data.get("icon") or "folder").strip()
            is_expense = category_type != "income"

        category = CategoryService.update_category(
            category_id=category_id,
            user_id=current_user.id,
            name=name,
            description=(data.get("description") or "").strip(),
            color=data.get("color") or "#6c757d",
            icon=icon,
            is_expense=is_expense,
            category_type=category_type,
        )

        response_type = category_type
        if category_type == "transfer":
            response_type = "transfer"
        elif not category.is_expense:
            response_type = "income"
        elif category.is_expense:
            response_type = "expense"

        return api_success(
            {
                "id": category.id,
                "name": category.name,
                "description": category.description or "",
                "type": response_type,
                "color": category.color or "#6c757d",
                "icon": category.icon or "folder",
                "is_default": getattr(category, "is_global", False),
                "created_at": (
                    category.created_at.isoformat()
                    if hasattr(category, "created_at") and category.created_at
                    else None
                ),
            }
        )

    except CategoryNotFoundError:
        return api_error("Catégorie introuvable", 404)
    except CategoryPermissionError:
        return api_error("Accès non autorisé", 403)
    except CategoryValidationError as e:
        return api_error(f"Données invalides: {e}", 400)
    except CategoryIntegrityError as e:
        return api_error(f"Conflit de données: {e}", 409)
    except Exception as e:
        logger.error(f"Erreur mise à jour catégorie {category_id}: {e}", exc_info=True)
        return api_error("Erreur lors de la mise à jour de la catégorie", 500)


@api_v1_bp.route("/categories/<int:category_id>", methods=["DELETE"])
@login_required
def delete_category(category_id):
    """Supprime une catégorie."""
    try:
        force_delete = request.args.get("force", "0").lower() in ("1", "true", "yes")

        CategoryService.delete_category(
            category_id=category_id,
            user_id=current_user.id,
            force=force_delete,
        )

        return api_success(message="Catégorie supprimée avec succès")

    except CategoryNotFoundError:
        return api_error("Catégorie introuvable", 404)
    except CategoryPermissionError:
        return api_error("Accès non autorisé", 403)
    except CategoryIntegrityError:
        return api_error(
            "La catégorie est utilisée dans des transactions",
            409,
            errors={"force_url": f"/api/v1/categories/{category_id}?force=1"},
        )
    except Exception as e:
        logger.error(f"Erreur suppression catégorie {category_id}: {e}", exc_info=True)
        return api_error("Erreur lors de la suppression de la catégorie", 500)
