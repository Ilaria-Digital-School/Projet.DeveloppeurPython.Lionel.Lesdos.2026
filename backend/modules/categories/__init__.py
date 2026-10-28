"""
Module pour la gestion des catégories de l'application.

Ce module contient les formulaires et les routes web pour la gestion des catégories.
Les modèles et services sont centralisés dans backend/core/.

Architecture :
- Formulaires WTForms : Validation et rendu des formulaires HTML
- Routes web Flask : Interface utilisateur pour la gestion des catégories
- Modèles : Importés depuis core/models/category.py
- Services métier : Importés depuis core/services/categories/
"""

try:
    from core.models.category import Category
    from core.services.categories.category_services import CategoryService

    from .category_forms import CategoryForm

    # Blueprint défini dans category_routes.py (source unique)
    from .category_routes import categories_bp  # noqa: F401

    __all__ = [
        "Category",
        "CategoryForm",
        "CategoryService",
        "categories_bp",
    ]

except ImportError as e:
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Erreur lors de l'import des modules categories: {e}", exc_info=True)
    raise
