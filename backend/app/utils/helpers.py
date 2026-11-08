"""
Fonctions utilitaires pour l'application.

Ce module contient des fonctions utilitaires réutilisables
dans toute l'application.
"""

from datetime import datetime

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CHF": "CHF"}


def paginate(query, page, per_page=20):
    """Effectue une pagination sur une requête SQLAlchemy.

    Args:
        query: La requête SQLAlchemy à paginer
        page (int): Numéro de la page (commence à 1)
        per_page (int, optional): Nombre d'éléments par page. Par défaut 20.

    Returns:
        dict: Un dictionnaire contenant les éléments de la page, le numéro de page,
              le nombre total de pages et le nombre total d'éléments
    """
    if page < 1:
        page = 1

    items = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "items": items.items,
        "page": page,
        "per_page": per_page,
        "total_pages": items.pages,
        "total_items": items.total,
        "has_prev": items.has_prev,
        "has_next": items.has_next,
        "prev_num": items.prev_num,
        "next_num": items.next_num,
    }


def get_current_financial_year():
    """Retourne l'année fiscale en cours.

    Returns:
        int: L'année fiscale en cours
    """
    today = datetime.now()
    return today.year if today.month >= 4 else today.year - 1
