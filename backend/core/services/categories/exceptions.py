"""
Exceptions personnalisées pour le module des catégories.
"""


class CategoryError(Exception):
    """Classe de base pour les erreurs liées aux catégories."""


class CategoryNotFoundError(CategoryError):
    """Lancée lorsqu'une catégorie n'est pas trouvée."""


class CategoryValidationError(CategoryError):
    """Lancée lors d'une erreur de validation des données d'une catégorie."""


class CategoryPermissionError(CategoryError):
    """Lancée lorsqu'un utilisateur n'a pas les droits sur une catégorie."""


class CategoryIntegrityError(CategoryError):
    """Lancée en cas de violation d'intégrité de la base de données."""
