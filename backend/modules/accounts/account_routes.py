"""
Routes pour la gestion des comptes bancaires.

Ce module contient les routes pour les opérations CRUD sur les comptes bancaires,
ainsi que les opérations spécifiques comme les transferts et les mises à jour de solde.
"""

from flask import (
    Blueprint,
    current_app,
    flash,
    render_template,
    request,
)
from flask_login import current_user, login_required

from core.models.account import Account

from .account_forms import AddAccountForm

# Création du blueprint
accounts_bp = Blueprint("accounts_bp", __name__, url_prefix="/comptes")


@accounts_bp.route("/")
@login_required
def index():
    """
    Affiche la liste des comptes de l'utilisateur.

    Query Parameters:
        active_only (bool): Si True, ne retourne que les comptes actifs (défaut: True)
        account_type (str): Filtre optionnel sur le type de compte

    Returns:
        Template HTML avec la liste des comptes
    """
    try:
        # Récupération des paramètres de filtre
        active_only = request.args.get("active_only", "true").lower() == "true"
        account_type = request.args.get("account_type")

        # Récupération des comptes directement via le modèle
        query = Account.query.filter_by(user_id=current_user.id)

        if active_only:
            query = query.filter(Account._is_active_db == True)

        if account_type:
            query = query.filter(Account._account_type_db == account_type)

        accounts = query.all()

        # Préparation des données pour le template
        total_balance = sum(getattr(account, "balance", 0) for account in accounts)

        # Initialisation du formulaire d'ajout de compte pour la modale
        form = AddAccountForm()

        return render_template(
            "accounts.html",
            accounts=accounts,
            total_balance=total_balance,
            active_only=active_only,
            selected_account_type=account_type,
            form=form,
        )

    except Exception as e:
        current_app.logger.error(
            f"Erreur lors de la récupération des comptes: {str(e)}"
        )
        flash(
            "Une erreur est survenue lors de la récupération de vos comptes.", "error"
        )
        return render_template("accounts.html", accounts=[])
