from flask import Blueprint, current_app, flash, render_template
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from core.models.category import Category

# Création du blueprint directement ici pour éviter les imports circulaires
categories_bp = Blueprint("categories", __name__, template_folder="templates")


@categories_bp.route("/")
@login_required  # Réactivé
def list_categories():
    """
    Affiche la liste des catégories de l'utilisateur

    GET /categories

    Returns:
        Rendu du template list.html avec la liste des catégories de l'utilisateur
    """
    try:
        current_app.logger.info(
            f"Tentative d'accès aux catégories pour l'utilisateur {current_user.id}"
        )

        # Uniquement les catégories personnelles : les modèles globaux
        # (user_id NULL) servent de gabarits copiés à l'inscription
        categories = (
            Category.query.filter(Category.user_id == current_user.id)
            .order_by(Category.name)
            .all()
        )

        # Calculer les statistiques de transactions pour chaque catégorie
        category_stats = {}
        for category in categories:
            if hasattr(category, "transactions"):
                category_stats[category.id] = category.transactions.count()
            else:
                category_stats[category.id] = 0

        return render_template(
            "categories.html", categories=categories, category_stats=category_stats
        )

    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Erreur base de données lors de la récupération des catégories: {e}",
            exc_info=True,
        )
        flash(
            "Une erreur est survenue lors de la récupération de vos catégories.",
            "danger",
        )
        # Retourner une page d'erreur au lieu de rediriger
        return render_template("categories.html", categories=[], category_stats={})
    except Exception as e:
        current_app.logger.error(
            f"Erreur inattendue lors de la récupération des catégories: {e}",
            exc_info=True,
        )
        flash("Une erreur inattendue est survenue.", "danger")
        # Retourner une page d'erreur au lieu de rediriger
        return render_template("categories.html", categories=[], category_stats={})
