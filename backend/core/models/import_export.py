"""
Modèles spécifiques pour l'import/export de données.
"""

from enum import Enum


class FileFormat(str, Enum):
    """Formats de fichiers supportés pour l'import/export."""

    CSV = "csv"
    JSON = "json"
    EXCEL = "xlsx"
