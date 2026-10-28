"""
Fonctions utilitaires pour les réponses API standardisées.
"""

from flask import jsonify


def api_success(data=None, message=None, status_code=200):
    """Réponse API de succès standardisée."""
    response = {"status": "success"}
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response["data"] = data
    if message:
        response["message"] = message
    return jsonify(response), status_code


def api_error(message, status_code=400, errors=None):
    """Réponse API d'erreur standardisée."""
    response = {"status": "error", "message": message}
    if errors:
        response["errors"] = errors
    return jsonify(response), status_code


def api_paginated(items, total, page, per_page):
    """Réponse API paginée standardisée."""
    return (
        jsonify(
            {
                "status": "success",
                "data": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
                },
            }
        ),
        200,
    )
