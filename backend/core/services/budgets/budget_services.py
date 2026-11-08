"""
Services pour la gestion des budgets.

Ce module contient la logique métier pour la gestion des budgets.
"""

from datetime import date, datetime, timezone

from flask import current_app
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from core.extensions import cache, db

# Import direct du modèle Budget (évite conflit SQLAlchemy)
from core.models.budget import Budget
from core.models.budget_history import BudgetHistory
from core.models.category import Category
from modules.dashboard.dashboard_forms import get_budget_form

# from modules.utils.email_utils import send_notification  # Module supprimé dans refonte


def _parse_date(valeur):
    """Date ISO (AAAA-MM-JJ) -> date ; None/"" -> None ; ValueError sinon."""
    if valeur in (None, ""):
        return None
    if isinstance(valeur, date):
        return valeur
    return date.fromisoformat(str(valeur)[:10])


def _valeur_historique(valeur):
    """Valeur sérialisable en JSON pour l'historique (Decimal, date...)."""
    from decimal import Decimal

    if isinstance(valeur, Decimal):
        return float(valeur)
    if isinstance(valeur, date):
        return valeur.isoformat()
    return valeur


def _to_bool(valeur):
    """Booléen JSON ou valeur de formulaire ("on", "true", "1")."""
    if isinstance(valeur, str):
        return valeur.strip().lower() in ("1", "true", "on", "yes", "oui")
    return bool(valeur)


def check_budget_notifications(user_id, today=None):
    """
    Vérifie les budgets de l'utilisateur et envoie une alerte quand un niveau
    est franchi sur la période en cours.

    Niveaux : le seuil du budget (notification_threshold, 90 % par défaut) puis
    100 % (dépassement). Chaque niveau n'est notifié qu'une fois par période
    (Budget.derniere_alerte), et tout repart à zéro à la période suivante.

    Args:
        user_id: ID de l'utilisateur
        today: date de référence (par défaut aujourd'hui ; utile aux tests)

    Returns:
        list: Liste des alertes envoyées
    """
    from core.services.notifications import NotificationService

    today = today or date.today()
    envoyees = []

    for budget in Budget.query.filter_by(user_id=user_id).all():
        try:
            periode = budget.periode_courante(today)
            budget_amount = budget.montant_disponible(today)
            if periode is None or budget_amount <= 0:
                continue
            period_start, period_end = periode

            spent = budget.get_used_amount(today)
            percentage = spent / budget_amount * 100
            seuil = budget.notification_threshold or 90
            niveau = (
                100 if percentage >= 100 else seuil if percentage >= seuil else None
            )
            if niveau is None:
                continue

            # Déjà notifié à ce niveau (ou plus) sur cette période ?
            cle_periode = period_start.isoformat()
            if budget.derniere_alerte:
                periode_alerte, _, niveau_alerte = budget.derniere_alerte.partition(":")
                if periode_alerte == cle_periode and int(niveau_alerte) >= niveau:
                    continue

            category_name = budget.category.name if budget.category else "Budget"
            if niveau == 100:
                type_alerte = "budget_exceeded"
                message = (
                    f"Budget dépassé pour {category_name}: {spent:.2f}€ dépensés "
                    f"sur {budget_amount:.2f}€ ({percentage:.0f}%)"
                )
            else:
                type_alerte = "budget_threshold"
                message = (
                    f"{seuil}% du budget atteint pour {category_name}: "
                    f"{spent:.2f}€ sur {budget_amount:.2f}€ ({percentage:.0f}%)"
                )

            NotificationService.send_notification(
                user_id=user_id,
                title=f"Alerte budget : {type_alerte.replace('_', ' ').title()}",
                message=message,
                notification_type="budget_alert",
                action_url="/dashboard/",
                send_email=True,
                metadata={
                    "budget_id": budget.id,
                    "budget_name": category_name,
                    "percentage": round(percentage, 1),
                    "current_amount": spent,
                    "budget_limit": budget_amount,
                    "threshold": niveau,
                    "period_start": cle_periode,
                    "period_end": period_end.isoformat(),
                },
            )
            budget.derniere_alerte = f"{cle_periode}:{niveau}"
            budget.notification_sent = True
            db.session.commit()
            envoyees.append(
                {
                    "type": type_alerte,
                    "budget_id": budget.id,
                    "threshold": niveau,
                    "percentage": round(percentage, 1),
                    "message": message,
                }
            )
            current_app.logger.info(f"Notification budget envoyée: {message}")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"Erreur lors de la vérification du budget {budget.id}: {str(e)}"
            )

    return envoyees


def export_budgets(user_id, format="csv"):
    """
    Exporte les budgets d'un utilisateur au format CSV ou Excel.

    Args:
        user_id: ID de l'utilisateur
        format: Format d'export ('csv' ou 'excel')

    Returns:
        tuple: (données exportées, nom de fichier, type MIME)
    """
    import csv
    import io
    from datetime import datetime

    try:
        # Récupérer les budgets de l'utilisateur avec les informations de catégorie
        budgets = (
            Budget.query.join(Category)
            .filter(Budget.user_id == user_id)
            .add_columns(
                Budget.id,
                Budget.amount,
                Budget.period,
                Budget.start_date,
                Budget.end_date,
                Category.name.label("category_name"),
            )
            .all()
        )

        # Préparer les données pour l'export
        data = []
        for budget in budgets:
            data.append(
                {
                    "ID": budget.id,
                    "Catégorie": budget.category_name,
                    "Montant": str(budget.amount) + " €",
                    "Période": budget.period,
                    "Date de début": (
                        budget.start_date.strftime("%Y-%m-%d")
                        if budget.start_date
                        else ""
                    ),
                    "Date de fin": (
                        budget.end_date.strftime("%Y-%m-%d") if budget.end_date else ""
                    ),
                }
            )

        if format.lower() == "csv":
            # Générer un fichier CSV
            output = io.StringIO()
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "ID",
                    "Catégorie",
                    "Montant",
                    "Période",
                    "Date de début",
                    "Date de fin",
                ],
                delimiter=";",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
            )

            writer.writeheader()
            for row in data:
                writer.writerow(row)

            output.seek(0)
            filename = f'budgets_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            return output.getvalue(), filename, "text/csv"

        elif format.lower() == "excel":
            # Générer un fichier Excel
            try:
                import pandas as pd

                df = pd.DataFrame(data)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, index=False, sheet_name="Budgets")

                output.seek(0)
                filename = (
                    f'budgets_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                )
                return (
                    output.getvalue(),
                    filename,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

            except ImportError:
                raise ValueError("Le module 'pandas' est requis pour l'export Excel")

        else:
            raise ValueError(
                "Format d'export non pris en charge. Utilisez 'csv' ou 'excel'."
            )

    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'export des budgets: {str(e)}")
        raise


def get_budget_history(budget_id, user_id, page=1, per_page=10):
    """
    Récupère l'historique des modifications d'un budget.

    Args:
        budget_id: ID du budget
        user_id: ID de l'utilisateur (pour vérification des permissions)
        page: Numéro de page (pour la pagination)
        per_page: Nombre d'éléments par page

    Returns:
        tuple: (liste des entrées d'historique, nombre total d'entrées, nombre de pages)
    """
    try:
        # Vérifier que l'utilisateur a accès à ce budget
        budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first()
        if not budget:
            return [], 0, 0

        # Récupérer l'historique avec pagination
        query = BudgetHistory.query.filter_by(budget_id=budget_id)

        # Compter le nombre total d'entrées
        total = query.count()

        # Calculer le nombre total de pages
        pages = (total + per_page - 1) // per_page

        # Appliquer la pagination
        history_entries = (
            query.order_by(BudgetHistory.changed_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        # Formater les résultats
        result = []
        for entry in history_entries:
            result.append(
                {
                    "id": entry.id,
                    "changed_at": entry.changed_at.isoformat(),
                    "action": entry.action,
                    "changes": entry.changes,
                    "ip_address": entry.ip_address,
                }
            )

        return result, total, pages

    except Exception as e:
        current_app.logger.error(
            f"Erreur lors de la récupération de l'historique du budget {budget_id}: {str(e)}"
        )
        raise


# @cache.memoize(timeout=300)  # Cache désactivé pour debug
def get_user_budgets_with_expenses(user_id, page=1, per_page=10):
    """Récupère les budgets d'un utilisateur avec pagination et calcul des dépenses."""
    try:
        query = Budget.query.filter_by(user_id=user_id)
        total = query.count()

        pagination = query.order_by(Budget.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        today = date.today()
        budgets = []
        for b in pagination.items:
            suivi = b.indicateurs(today)
            budgets.append(
                {
                    **suivi,
                    "id": b.id,
                    "category_id": b.category_id,
                    "category_name": (
                        b.category.name if b.category else "Toutes catégories"
                    ),
                    "amount": float(b.amount),
                    "period": b.period,
                    "start_date": b.start_date.isoformat() if b.start_date else None,
                    "end_date": b.end_date.isoformat() if b.end_date else None,
                    "notification_threshold": b.notification_threshold or 90,
                    "report_actif": bool(b.report_actif),
                }
            )

        # Vérifier et envoyer des notifications si nécessaire
        check_budget_notifications(user_id)

        return {
            "items": budgets,
            "total": total,
            "pages": pagination.pages,
            "current_page": page,
            "per_page": per_page,
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erreur lors de la récupération des budgets: {str(e)}"
        )
        return {
            "items": [],
            "total": 0,
            "pages": 0,
            "current_page": 1,
            "per_page": per_page,
        }


def create_budget(user_id, data=None, form_data=None, ip_address=None):
    """
    Crée un nouveau budget pour un utilisateur.

    Args:
        user_id (int): ID de l'utilisateur propriétaire du budget
        data (dict, optional): Données du budget (pour compatibilité avec l'ancienne API)
        form_data (dict, optional): Données du formulaire (nouvelle API)
        ip_address (str, optional): Adresse IP de l'utilisateur pour l'historique

    Returns:
        tuple: (success, result, status_code) où :
            - success (bool): True si l'opération a réussi, False sinon
            - result (Budget|str): Le budget créé en cas de succès, message d'erreur sinon
            - status_code (int): Code HTTP approprié
    """
    try:
        # Gérer la compatibilité avec l'ancienne API
        form_data = form_data or data
        if form_data is None:
            return False, "Aucune donnée fournie", 400

        # Validation manuelle des données requises
        if not form_data.get("category_id"):
            return False, "La catégorie est requise", 400
        if not form_data.get("amount"):
            return False, "Le montant est requis", 400

        try:
            amount = float(form_data.get("amount"))
            if amount <= 0:
                return False, "Le montant doit être positif", 400
        except ValueError, TypeError:
            return False, "Le montant doit être un nombre valide", 400

        try:
            category_id = int(form_data.get("category_id"))
        except ValueError, TypeError:
            return False, "L'ID de catégorie doit être un nombre valide", 400

        # Vérifier que la catégorie existe et appartient à l'utilisateur
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()

        if not category:
            return False, "Catégorie non trouvée ou accès non autorisé", 404

        # Valeurs par défaut et conversion
        period = form_data.get("period") or "monthly"
        if period not in ("monthly", "yearly", "custom"):
            return False, "Période invalide (monthly, yearly ou custom)", 400
        try:
            notification_threshold = int(form_data.get("notification_threshold") or 90)
        except ValueError, TypeError:
            return False, "Le seuil d'alerte doit être un entier", 400
        if not 1 <= notification_threshold <= 100:
            return False, "Le seuil d'alerte doit être entre 1 et 100", 400

        # Dates : mensuel -> début du mois, annuel -> 1er janvier ; une date de
        # début fournie est respectée. Personnalisé : début et fin requis.
        try:
            start_date = _parse_date(form_data.get("start_date"))
            end_date = _parse_date(form_data.get("end_date"))
        except ValueError:
            return False, "Date invalide (format attendu : AAAA-MM-JJ)", 400
        today = date.today()
        if period == "custom":
            if not start_date or not end_date:
                return (
                    False,
                    "Les dates de début et de fin sont requises pour une période personnalisée",
                    400,
                )
        elif not start_date:
            start_date = (
                today.replace(month=1, day=1)
                if period == "yearly"
                else today.replace(day=1)
            )
        if end_date and end_date < start_date:
            return False, "La date de fin doit être postérieure à la date de début", 400

        # Le report n'a de sens que pour des périodes qui se répètent
        report_actif = _to_bool(form_data.get("report_actif")) and period != "custom"

        # Créer le budget
        budget = Budget(
            user_id=user_id,
            category_id=category.id,
            amount=amount,
            period=period,
            start_date=start_date,
            end_date=end_date,
            notification_threshold=notification_threshold,
            report_actif=report_actif,
        )

        db.session.add(budget)
        db.session.flush()

        if ip_address:
            db.session.add(
                BudgetHistory(
                    budget_id=budget.id,
                    user_id=user_id,
                    action="create",
                    changes={
                        "category_id": category.id,
                        "category_name": category.name,
                        "amount": amount,
                        "period": period,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat() if end_date else None,
                        "notification_threshold": notification_threshold,
                        "report_actif": report_actif,
                    },
                    ip_address=ip_address,
                )
            )

        db.session.commit()

        # Invalider le cache des budgets
        cache_key = f"user_budgets_{user_id}"
        cache.delete(cache_key)

        return True, budget, 201

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erreur base de données lors de la création du budget: {str(e)}"
        )
        return False, "Erreur lors de la création du budget", 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erreur inattendue lors de la création du budget: {str(e)}"
        )
        return False, "Une erreur inattendue est survenue", 500


def update_budget(budget_id, user_id, data=None, form_data=None, ip_address=None):
    """
    Met à jour un budget existant.

    Args:
        budget_id (int): ID du budget à mettre à jour
        user_id (int): ID de l'utilisateur effectuant la mise à jour
        data (dict, optional): Données de mise à jour (ancienne API)
        form_data (dict, optional): Données du formulaire (nouvelle API)
        ip_address (str, optional): Adresse IP de l'utilisateur (pour l'historique)

    Returns:
        tuple: (success, result, status_code) où :
            - success (bool): True si l'opération a réussi, False sinon
            - result (Budget|str): Le budget mis à jour en cas de succès, message d'erreur sinon
            - status_code (int): Code HTTP approprié
    """
    # Gérer la compatibilité avec l'ancienne API
    form_data = form_data or data
    if form_data is None:
        return False, "Aucune donnée fournie", 400

    try:
        # Récupérer le budget
        budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first()
        if not budget:
            return False, "Budget non trouvé ou accès non autorisé", 404

        # Créer le formulaire avec les données existantes et les nouvelles données
        form = get_budget_form(
            {
                **{
                    "id": budget.id,
                    "name": budget.category.name if budget.category else "",
                    "category_id": budget.category_id,
                    "amount": float(budget.amount) if budget.amount else 0,
                    "period": budget.period,
                    "start_date": budget.start_date,
                    "end_date": budget.end_date,
                    "notification_threshold": budget.notification_threshold,
                },
                **form_data,
            },
            csrf_enabled=False,
        )

        # Valider le formulaire
        if not form.validate():
            error_messages = ", ".join(
                [
                    f"{field}: {', '.join(errors)}"
                    for field, errors in form.errors.items()
                ]
            )
            return False, f"Données invalides: {error_messages}", 400

        # Vérifier que la catégorie existe et appartient à l'utilisateur
        category_id = (
            form.category_id.data if "category_id" in form_data else budget.category_id
        )
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()

        if not category:
            return False, "Catégorie non trouvée ou accès non autorisé", 404

        # Préparer les nouvelles valeurs
        new_values = {
            "category_id": category.id,
            "amount": form.amount.data if "amount" in form_data else budget.amount,
            "period": form.period.data if "period" in form_data else budget.period,
            "start_date": (
                form.start_date.data if "start_date" in form_data else budget.start_date
            ),
            "end_date": (
                form.end_date.data
                if ("end_date" in form_data and form.period.data == "custom")
                else (budget.end_date if budget.period == "custom" else None)
            ),
            "notification_threshold": (
                form.notification_threshold.data
                if "notification_threshold" in form_data
                else budget.notification_threshold
            ),
        }

        # Vérifier les conflits de périodes pour la même catégorie
        if any(
            field in form_data
            for field in ["category_id", "start_date", "end_date", "period"]
        ):
            existing_budget = Budget.query.filter(
                Budget.id != budget_id,  # Exclure le budget actuel
                Budget.user_id == user_id,
                Budget.category_id == new_values["category_id"],
                # Deux périodes se chevauchent si chacune commence avant la fin
                # de l'autre (fin absente = sans fin). Comparer end_date à None
                # levait une erreur SQLAlchemy : aucun budget mensuel (sans date
                # de fin) ne pouvait être modifié.
                or_(
                    Budget.end_date.is_(None),
                    Budget.end_date >= new_values["start_date"],
                ),
                *(
                    [Budget.start_date <= new_values["end_date"]]
                    if new_values["end_date"] is not None
                    else []
                ),
            ).first()

            if existing_budget:
                return (
                    False,
                    "Un budget existe déjà pour cette catégorie sur cette période",
                    409,
                )

        if "report_actif" in form_data:
            new_values["report_actif"] = _to_bool(form_data["report_actif"])
        if new_values["period"] == "custom":
            new_values["report_actif"] = False

        # Différences avant -> après, pour l'historique
        changes = {}
        for key, value in new_values.items():
            ancien = _valeur_historique(getattr(budget, key))
            nouveau = _valeur_historique(value)
            if ancien != nouveau:
                changes[key] = {"old": ancien, "new": nouveau}

        # Mettre à jour le budget
        for key, value in new_values.items():
            setattr(budget, key, value)

        budget.updated_at = datetime.now(timezone.utc)

        # Enregistrer l'historique des modifications
        if ip_address and changes:
            db.session.add(
                BudgetHistory(
                    budget_id=budget.id,
                    user_id=user_id,
                    action="update",
                    changes=changes,
                    ip_address=ip_address,
                )
            )

        # Valider les changements
        db.session.commit()

        # Invalider le cache
        cache_key = f"user_budgets_{user_id}"
        cache.delete(cache_key)

        return True, budget, 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erreur base de données lors de la mise à jour du budget: {str(e)}"
        )
        return False, "Erreur lors de la mise à jour du budget", 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erreur inattendue lors de la mise à jour du budget: {str(e)}"
        )
        return (
            False,
            "Une erreur inattendue est survenue lors de la mise à jour du budget",
            500,
        )


def delete_budget(budget_id, user_id, ip_address=None):
    """
    Supprime un budget de manière logique (soft delete).

    Args:
        budget_id (int): ID du budget à supprimer
        user_id (int): ID de l'utilisateur effectuant la suppression
        ip_address (str, optional): Adresse IP de l'utilisateur (pour l'historique)

    Returns:
        tuple: (success, message, status_code) où :
            - success (bool): True si l'opération a réussi, False sinon
            - message (str): Message de succès ou d'erreur
            - status_code (int): Code HTTP approprié
    """
    try:
        current_app.logger.info(
            f"🗑️ DELETE_BUDGET: budget_id={budget_id}, user_id={user_id}"
        )

        # Récupérer le budget
        budget = Budget.query.filter_by(id=budget_id, user_id=user_id).first()
        current_app.logger.info(f"🔍 Budget trouvé: {budget}")

        if not budget:
            current_app.logger.error(
                f"❌ Budget {budget_id} non trouvé pour user {user_id}"
            )
            return False, "Budget non trouvé ou accès non autorisé", 404

        # Enregistrer l'historique avant suppression
        if ip_address:
            try:
                # Instantané du budget supprimé (budget_id passera à NULL)
                history = BudgetHistory(
                    budget_id=budget.id,
                    user_id=user_id,
                    action="delete",
                    changes={
                        "category_id": budget.category_id,
                        "category_name": (
                            budget.category.name if budget.category else None
                        ),
                        "amount": float(budget.amount),
                        "period": budget.period,
                        "start_date": budget.start_date.isoformat(),
                        "end_date": (
                            budget.end_date.isoformat() if budget.end_date else None
                        ),
                        "report_actif": bool(budget.report_actif),
                    },
                    ip_address=ip_address,
                )
                db.session.add(history)
            except Exception as e:
                current_app.logger.warning(f"Erreur création historique: {e}")

        # Effectuer une suppression réelle
        db.session.delete(budget)

        db.session.commit()

        # Invalider le cache
        cache_key = f"user_budgets_{user_id}"
        cache.delete(cache_key)

        return True, "Budget supprimé avec succès", 200

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erreur base de données lors de la suppression du budget {budget_id}: {str(e)}"
        )
        return False, "Erreur lors de la suppression du budget", 500

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Erreur inattendue lors de la suppression du budget {budget_id}: {str(e)}"
        )
        return (
            False,
            "Une erreur inattendue est survenue lors de la suppression du budget",
            500,
        )


def get_budget_by_id(budget_id, user_id):
    """
    Récupère un budget spécifique par son ID pour un utilisateur donné.

    Args:
        budget_id (int): ID du budget à récupérer
        user_id (int): ID de l'utilisateur propriétaire

    Returns:
        Budget|None: Le budget trouvé ou None si non trouvé/non autorisé
    """
    try:
        budget = Budget.query.filter(
            Budget.id == budget_id, Budget.user_id == user_id
        ).first()

        return budget

    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Erreur lors de la récupération du budget {budget_id}: {str(e)}"
        )
        return None
    except Exception as e:
        current_app.logger.error(
            f"Erreur inattendue lors de la récupération du budget {budget_id}: {str(e)}"
        )
        return None
