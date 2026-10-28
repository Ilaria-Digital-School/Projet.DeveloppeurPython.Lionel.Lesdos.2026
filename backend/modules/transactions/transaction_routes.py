"""
Routes pour la gestion des transactions financières.

Ce module contient toutes les routes Flask pour la gestion des transactions,
incluant la création, modification, suppression et consultation des transactions.

Architecture:
- Utilise les services métier centralisés pour la logique business
- Gestion d'erreurs standardisée
- Logging configuré pour le suivi des opérations
"""

import logging

from flask import flash, render_template, request
from flask_login import current_user, login_required

from app.utils.errors import ValidationError
from core.services.transactions import TransactionService

from .transaction_forms import TransactionForm

# Configuration du logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Import du blueprint depuis __init__.py pour cohérence
from . import web_bp

# Utiliser directement web_bp qui est défini comme 'transactions' dans __init__.py
transactions_bp = web_bp


@transactions_bp.route("/")
@login_required
def list_transactions():
    """Affiche la liste des transactions de l'utilisateur."""
    logger.info(
        f"Accès à la liste des transactions pour l'utilisateur {current_user.id}"
    )

    try:
        # Récupérer les paramètres de pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        # Utiliser le service métier pour récupérer les transactions
        service = TransactionService()
        result = service.get_user_transactions(
            user_id=current_user.id, page=page, per_page=per_page
        )

        if result:
            logger.info(
                f"Récupération de {len(result.get('items', []))} transactions pour l'utilisateur {current_user.id}"
            )
            # Créer un formulaire vide pour le template
            form = TransactionForm()
            return render_template(
                "transactions.html",
                transactions=result.get("items", []),
                pagination=result.get("pagination"),
                form=form,
                accounts=service.get_user_accounts(current_user.id),
                categories=service.get_user_categories(current_user.id),
            )
        else:
            flash("Aucune transaction trouvée.", "info")
            # Créer un formulaire vide pour le template
            form = TransactionForm()
            return render_template(
                "transactions.html",
                transactions=[],
                pagination=None,
                form=form,
                accounts=service.get_user_accounts(current_user.id),
                categories=service.get_user_categories(current_user.id),
            )

    except ValidationError as e:
        logger.warning(
            f"Erreur de validation lors de la récupération des transactions: {e}"
        )
        flash(f"Erreur de validation: {e}", "warning")
        # Créer un formulaire vide pour le template
        form = TransactionForm()
        service = TransactionService()
        # Afficher l'erreur au lieu de rediriger
        return render_template(
            "transactions.html",
            transactions=[],
            pagination=None,
            error=str(e),
            form=form,
            accounts=service.get_user_accounts(current_user.id),
            categories=service.get_user_categories(current_user.id),
        )
    except Exception as e:
        logger.error(
            f"Erreur lors de la récupération des transactions pour l'utilisateur {current_user.id}: {e}"
        )
        flash(f"Erreur: {str(e)}", "danger")
        # Créer un formulaire vide pour le template
        form = TransactionForm()
        service = TransactionService()
        # Afficher l'erreur au lieu de rediriger
        return render_template(
            "transactions.html",
            transactions=[],
            pagination=None,
            error=str(e),
            form=form,
            accounts=service.get_user_accounts(current_user.id),
            categories=service.get_user_categories(current_user.id),
        )
