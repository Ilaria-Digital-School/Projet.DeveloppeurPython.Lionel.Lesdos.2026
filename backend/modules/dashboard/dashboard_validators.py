"""
Validateurs pour le module de tableau de bord
"""

import re
from datetime import datetime

from wtforms import ValidationError


def validate_date_format(date_str):
    """Valide le format de date YYYY-MM-DD"""
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Le format de date doit être YYYY-MM-DD")


def validate_date_range(start_date, end_date):
    """Valide que la date de début est avant la date de fin"""
    if start_date and end_date and start_date > end_date:
        raise ValidationError("La date de début doit être antérieure à la date de fin")


def validate_export_format(fmt):
    """Valide le format d'export"""
    if fmt.lower() not in ("json", "csv"):
        raise ValidationError("Le format d'export doit être 'json' ou 'csv'")
    return fmt.lower()


def validate_limit(limit, max_limit=100):
    """Valide la limite de résultats"""
    try:
        limit = int(limit)
        if not (1 <= limit <= max_limit):
            raise ValueError()
        return limit
    except ValueError, TypeError:
        raise ValidationError(f"La limite doit être un entier entre 1 et {max_limit}")


def sanitize_search_query(query):
    """Nettoie et valide une requête de recherche"""
    if not query or not isinstance(query, str):
        return ""

    # Suppression des caractères potentiellement dangereux
    sanitized = re.sub(r"[^\w\s\-]", "", query.strip())
    return sanitized[:100]  # Limite à 100 caractères
