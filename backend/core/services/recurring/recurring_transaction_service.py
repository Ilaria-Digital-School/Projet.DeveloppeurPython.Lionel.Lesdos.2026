"""
Service pour la gestion des transactions récurrentes.

Gère la création, modification, pause/reprise et exécution automatique
des transactions récurrentes.
"""

import calendar
import logging
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.exc import SQLAlchemyError

from core.extensions import db
from core.models.recurring_transaction import RecurringTransaction
from core.services.transactions.transaction_services import TransactionService

logger = logging.getLogger(__name__)

# Plafond d'occurrences rattrapées par récurrence et par exécution
# (ex. récurrence quotidienne restée en retard des années)
MAX_RATTRAPAGE = 366

# Échecs consécutifs avant mise en pause automatique d'une récurrence
MAX_ECHECS = 3


class RecurringTransactionService:
    """Service pour les transactions récurrentes"""

    @staticmethod
    def create_recurring(user_id, data):
        """
        Crée un template de transaction récurrente.

        Args:
            user_id: ID de l'utilisateur
            data: dict avec les champs du template

        Returns:
            tuple: (success, result_or_error, status_code)
        """
        try:
            montant = data.get("montant") or data.get("amount")
            if not montant or float(montant) <= 0:
                return False, "Le montant doit être positif", 400

            account_id = data.get("account_id")
            if not account_id:
                return False, "Le compte est requis", 400

            type_transaction = data.get("type_transaction", "expense")
            libelle = data.get("libelle") or data.get("description", "")
            if not libelle:
                return False, "Le libellé est requis", 400

            frequency = data.get("frequency", "monthly")
            if frequency not in ("daily", "weekly", "monthly", "yearly"):
                return False, "Fréquence invalide", 400

            interval = int(data.get("interval", 1))
            start_date_str = data.get("start_date")
            start = (
                date.fromisoformat(start_date_str) if start_date_str else date.today()
            )

            end_date_str = data.get("end_date")
            end = date.fromisoformat(end_date_str) if end_date_str else None

            day_of_month = data.get("day_of_month")
            day_of_week = data.get("day_of_week")
            if day_of_month is not None:
                day_of_month = int(day_of_month)
            if day_of_week is not None:
                day_of_week = int(day_of_week)

            # La première exécution a lieu à la date de début elle-même
            # (le scheduler exécute tout ce qui est <= aujourd'hui)
            today = date.today()
            if start >= today:
                next_date = start
            else:
                # Date de début passée : prochaine occurrence depuis aujourd'hui
                next_date = RecurringTransactionService._calculate_next_date(
                    today, frequency, interval, day_of_month, day_of_week
                )

            recurring = RecurringTransaction(
                user_id=user_id,
                account_id=int(account_id),
                destination_account_id=(
                    int(data["destination_account_id"])
                    if data.get("destination_account_id")
                    else None
                ),
                category_id=(
                    int(data["category_id"]) if data.get("category_id") else None
                ),
                montant=Decimal(str(montant)),
                type_transaction=type_transaction,
                libelle=libelle,
                notes=data.get("notes"),
                devise=data.get("devise", "EUR"),
                frequency=frequency,
                interval=interval,
                day_of_month=day_of_month,
                day_of_week=day_of_week,
                start_date=start,
                end_date=end,
                next_execution_date=next_date,
                is_active=True,
            )

            db.session.add(recurring)
            db.session.commit()

            logger.info(
                f"Transaction récurrente créée: id={recurring.id}, user={user_id}, '{libelle}'"
            )
            return True, recurring, 201

        except (ValueError, TypeError) as e:
            return False, f"Données invalides: {str(e)}", 400
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur DB création récurrente: {e}")
            return False, "Erreur lors de la création", 500

    @staticmethod
    def update_recurring(recurring_id, user_id, data):
        """Met à jour les paramètres d'une transaction récurrente."""
        try:
            recurring = RecurringTransaction.query.filter_by(
                id=recurring_id, user_id=user_id
            ).first()

            if not recurring:
                return False, "Transaction récurrente non trouvée", 404

            # Mettre à jour les champs fournis
            updatable = [
                "account_id",
                "destination_account_id",
                "category_id",
                "montant",
                "type_transaction",
                "libelle",
                "notes",
                "devise",
                "frequency",
                "interval",
                "day_of_month",
                "day_of_week",
            ]
            for field in updatable:
                if field in data:
                    value = data[field]
                    if field == "montant" and value is not None:
                        value = Decimal(str(value))
                    if (
                        field
                        in (
                            "account_id",
                            "destination_account_id",
                            "category_id",
                            "interval",
                            "day_of_month",
                            "day_of_week",
                        )
                        and value is not None
                    ):
                        value = int(value) if value != "" else None
                    setattr(recurring, field, value)

            if "start_date" in data and data["start_date"]:
                recurring.start_date = date.fromisoformat(data["start_date"])
            if "end_date" in data:
                recurring.end_date = (
                    date.fromisoformat(data["end_date"]) if data["end_date"] else None
                )

            # Recalculer la prochaine date
            if (
                recurring.last_executed_date is None
                and recurring.start_date >= date.today()
            ):
                # Jamais exécutée : la première exécution reste la date de début
                recurring.next_execution_date = recurring.start_date
            else:
                base = recurring.last_executed_date or recurring.start_date
                recurring.next_execution_date = (
                    RecurringTransactionService._calculate_next_date(
                        base,
                        recurring.frequency,
                        recurring.interval,
                        recurring.day_of_month,
                        recurring.day_of_week,
                    )
                )

            db.session.commit()
            logger.info(f"Transaction récurrente {recurring_id} mise à jour")
            return True, recurring, 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur DB mise à jour récurrente {recurring_id}: {e}")
            return False, "Erreur lors de la mise à jour", 500

    @staticmethod
    def delete_recurring(recurring_id, user_id):
        """Supprime définitivement une transaction récurrente."""
        try:
            recurring = RecurringTransaction.query.filter_by(
                id=recurring_id, user_id=user_id
            ).first()

            if not recurring:
                return False, "Transaction récurrente non trouvée", 404

            db.session.delete(recurring)
            db.session.commit()

            logger.info(f"Transaction récurrente {recurring_id} supprimée")
            return True, "Transaction récurrente supprimée", 200

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Erreur DB suppression récurrente {recurring_id}: {e}")
            return False, "Erreur lors de la suppression", 500

    @staticmethod
    def get_user_recurring(user_id, include_inactive=False):
        """Liste les transactions récurrentes d'un utilisateur."""
        query = RecurringTransaction.query.filter_by(user_id=user_id)
        if not include_inactive:
            query = query.filter_by(is_active=True)

        return query.order_by(RecurringTransaction.next_execution_date.asc()).all()

    @staticmethod
    def get_recurring_by_id(recurring_id, user_id):
        """Récupère une transaction récurrente par ID."""
        return RecurringTransaction.query.filter_by(
            id=recurring_id, user_id=user_id
        ).first()

    @staticmethod
    def pause_recurring(recurring_id, user_id):
        """Met en pause une transaction récurrente."""
        recurring = RecurringTransaction.query.filter_by(
            id=recurring_id, user_id=user_id
        ).first()

        if not recurring:
            return False, "Transaction récurrente non trouvée", 404

        recurring.is_active = False
        db.session.commit()
        return True, "Transaction récurrente mise en pause", 200

    @staticmethod
    def resume_recurring(recurring_id, user_id):
        """Reprend une transaction récurrente mise en pause."""
        recurring = RecurringTransaction.query.filter_by(
            id=recurring_id, user_id=user_id
        ).first()

        if not recurring:
            return False, "Transaction récurrente non trouvée", 404

        recurring.is_active = True
        recurring.echecs_consecutifs = 0
        recurring.derniere_erreur = None
        # Conserver la prochaine occurrence si elle est encore à venir
        # (évite de sauter l'occurrence du jour lors d'un pause/reprise).
        # Sinon, recalculer depuis aujourd'hui sans rattrapage rétroactif.
        today = date.today()
        if not recurring.next_execution_date or recurring.next_execution_date < today:
            recurring.next_execution_date = (
                RecurringTransactionService._calculate_next_date(
                    today,
                    recurring.frequency,
                    recurring.interval,
                    recurring.day_of_month,
                    recurring.day_of_week,
                )
            )
        db.session.commit()
        return True, "Transaction récurrente reprise", 200

    @staticmethod
    def process_due_transactions():
        """
        Traite toutes les transactions récurrentes dues.
        Appelé par le cron job (flask recurring process).

        Returns:
            int: Nombre de transactions créées
        """
        today = date.today()
        count = 0

        # Récupérer toutes les récurrences actives dont la date est atteinte
        due = RecurringTransaction.query.filter(
            RecurringTransaction.is_active == True,
            RecurringTransaction.next_execution_date <= today,
        ).all()

        logger.info(f"Processing {len(due)} transactions récurrentes dues")

        utilisateurs, comptes = set(), set()
        for recurring in due:
            recurring_id = recurring.id
            try:
                # Rattrapage : une transaction par occurrence manquée (scheduler
                # arrêté), datée de sa date prévue ; la suivante est calculée
                # depuis la date prévue pour ne pas dériver (loyer du 5 reste le 5)
                executees = 0
                while (
                    recurring.next_execution_date <= today
                    and executees < MAX_RATTRAPAGE
                ):
                    occurrence = recurring.next_execution_date
                    if recurring.end_date and occurrence > recurring.end_date:
                        break

                    # commit=False : toutes les occurrences de la récurrence et
                    # l'avancement de la date sont validés ensemble ou pas du tout
                    TransactionService.create_transaction(
                        user_id=recurring.user_id,
                        account_id=recurring.account_id,
                        amount=recurring.montant,
                        transaction_type=recurring.type_transaction,
                        description=f"{recurring.libelle} (récurrent)",
                        transaction_date=occurrence,
                        category_id=recurring.category_id,
                        destination_account_id=recurring.destination_account_id,
                        notes=recurring.notes,
                        commit=False,
                    )

                    recurring.last_executed_date = occurrence
                    recurring.next_execution_date = (
                        RecurringTransactionService._calculate_next_date(
                            occurrence,
                            recurring.frequency,
                            recurring.interval,
                            recurring.day_of_month,
                            recurring.day_of_week,
                        )
                    )
                    # create_transaction(commit=False) expire la session :
                    # flusher avant le tour suivant pour ne pas perdre les dates
                    db.session.flush()
                    executees += 1

                # Date de fin atteinte : désactiver la récurrence
                if (
                    recurring.end_date
                    and recurring.next_execution_date > recurring.end_date
                ):
                    recurring.is_active = False

                recurring.echecs_consecutifs = 0
                recurring.derniere_erreur = None
                db.session.commit()
                count += executees
                logger.info(
                    f"Transaction récurrente {recurring_id} : {executees} occurrence(s) "
                    f"créée(s), prochaine: {recurring.next_execution_date}"
                )
                if executees:
                    RecurringTransactionService._notifier_execution(
                        recurring, executees
                    )
                    utilisateurs.add(recurring.user_id)
                    comptes.update(
                        c
                        for c in (
                            recurring.account_id,
                            recurring.destination_account_id,
                        )
                        if c
                    )

            except Exception as e:
                db.session.rollback()
                logger.error(
                    f"Erreur exécution récurrence {recurring_id}: {e}", exc_info=True
                )
                RecurringTransactionService._enregistrer_echec(recurring_id, e)
                continue

        # Contrôles faits par create_transaction hors import en lot (commit=False) :
        # alerte de solde faible et dépassements de budget
        RecurringTransactionService._verifier_apres_execution(utilisateurs, comptes)

        logger.info(f"Processing terminé: {count}/{len(due)} transactions créées")
        return count

    @staticmethod
    def _enregistrer_echec(recurring_id, erreur):
        """Compte l'échec, prévient l'utilisateur, met en pause après MAX_ECHECS."""
        from shared.exceptions import AppError

        try:
            recurring = db.session.get(RecurringTransaction, recurring_id)
            if recurring is None:
                return
            # Message lisible pour l'utilisateur ; pas de détail technique interne
            raison = (
                str(erreur) if isinstance(erreur, AppError) else "erreur inattendue"
            )[:255]
            recurring.echecs_consecutifs = (recurring.echecs_consecutifs or 0) + 1
            recurring.derniere_erreur = raison
            en_pause = recurring.echecs_consecutifs >= MAX_ECHECS
            if en_pause:
                recurring.is_active = False
            db.session.commit()

            # Prévenir au premier échec et à la mise en pause (pas chaque nuit)
            if recurring.echecs_consecutifs == 1 or en_pause:
                from core.services.notifications import NotificationService

                if en_pause:
                    titre = "Transaction récurrente suspendue"
                    message = (
                        f"'{recurring.libelle}' a échoué {recurring.echecs_consecutifs} "
                        f"fois de suite ({raison}) et a été mise en pause. "
                        "Corrigez le problème puis reprenez-la."
                    )
                else:
                    titre = "Échec d'une transaction récurrente"
                    message = (
                        f"'{recurring.libelle}' n'a pas pu être enregistrée : {raison}. "
                        "Nouvel essai au prochain passage."
                    )
                NotificationService.send_notification(
                    user_id=recurring.user_id,
                    title=titre,
                    message=message,
                    notification_type="recurring_failed",
                    action_url="/transactions/recurring",
                    send_email=True,
                    metadata={
                        "recurring_id": recurring.id,
                        "echecs": recurring.echecs_consecutifs,
                        "en_pause": en_pause,
                    },
                )
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur enregistrement échec récurrence {recurring_id}: {e}")

    @staticmethod
    def _notifier_execution(recurring, executees):
        """Une notification par récurrence exécutée (pas une par occurrence)."""
        try:
            from core.services.notifications import NotificationService

            NotificationService.send_notification(
                user_id=recurring.user_id,
                title="Transaction récurrente enregistrée",
                message=(
                    f"'{recurring.libelle}' : {executees} occurrence(s) de "
                    f"{recurring.montant}€ enregistrée(s)."
                ),
                notification_type="recurring_executed",
                action_url="/transactions/",
                send_email=False,
                metadata={"recurring_id": recurring.id, "occurrences": executees},
            )
        except Exception as e:
            logger.warning(f"Notification récurrence {recurring.id} non envoyée: {e}")

    @staticmethod
    def _verifier_apres_execution(utilisateurs, comptes):
        try:
            from core.models.account import Account
            from core.services.accounts.account_services import AccountService
            from core.services.budgets.budget_services import check_budget_notifications

            for compte_id in comptes:
                compte = db.session.get(Account, compte_id)
                if compte is not None:
                    AccountService._check_low_balance_alert(compte, compte.user_id)
            for user_id in utilisateurs:
                check_budget_notifications(user_id)
        except Exception as e:
            logger.warning(f"Contrôles après exécution des récurrences: {e}")

    @staticmethod
    def _calculate_next_date(
        from_date, frequency, interval=1, day_of_month=None, day_of_week=None
    ):
        """
        Calcule la prochaine date d'exécution à partir d'une date de référence.

        Args:
            from_date: date de référence
            frequency: 'daily', 'weekly', 'monthly', 'yearly'
            interval: tous les N périodes
            day_of_month: jour du mois (1-31) pour monthly
            day_of_week: jour de la semaine (0=lundi) pour weekly

        Returns:
            date: prochaine date d'exécution
        """
        if frequency == "daily":
            return from_date + timedelta(days=interval)

        elif frequency == "weekly":
            if day_of_week is None:
                return from_date + timedelta(weeks=interval)
            days_ahead = (day_of_week - from_date.weekday()) % 7
            if days_ahead == 0:
                # from_date est une occurrence : sauter de N semaines
                return from_date + timedelta(weeks=interval)
            # from_date n'est pas sur le bon jour : prochain jour voulu
            return from_date + timedelta(days=days_ahead)

        elif frequency == "monthly":
            next_d = from_date + relativedelta(months=interval)
            if day_of_month is not None:
                # Le 29/30/31 tombe le dernier jour des mois plus courts
                dernier_jour = calendar.monthrange(next_d.year, next_d.month)[1]
                next_d = next_d.replace(day=min(day_of_month, dernier_jour))
            return next_d

        elif frequency == "yearly":
            return from_date + relativedelta(years=interval)

        # Fallback
        return from_date + timedelta(days=30)
