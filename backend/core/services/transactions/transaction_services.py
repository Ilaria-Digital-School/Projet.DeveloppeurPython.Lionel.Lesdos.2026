"""
Services pour la gestion des transactions financières.

Ce module contient la logique métier pour les opérations sur les transactions,
y compris la création, la mise à jour, la suppression et les requêtes complexes.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import extract, func, or_
from sqlalchemy.exc import SQLAlchemyError

from core.extensions import db
from core.models.account import Account
from core.models.category import Category
from core.models.transactions import Transaction, TransactionType
from shared.exceptions import (
    AccountNotFoundError,
    CategoryNotFoundError,
    DatabaseError,
    InsufficientFundsError,
    InvalidTransactionError,
    TransactionNotFoundError,
)

logger = logging.getLogger(__name__)


def effets_sur_soldes(transaction) -> Dict[int, Decimal]:
    """Effet d'une transaction sur les soldes, par compte : {account_id: delta}.

    Mêmes règles que create_transaction / delete_transaction : seules les
    transactions 'completed' comptent ; dépense = -(montant + frais), revenu =
    montant - frais, virement avec destination = -(montant + frais) sur la
    source et +montant sur la destination ; virement sans destination : aucun.
    """
    if transaction.statut != "completed":
        return {}
    montant = Decimal(str(transaction.montant or 0))
    frais = Decimal(str(transaction.frais_transaction or 0))
    type_ = transaction.type_transaction
    if type_ in TransactionType.expense_values():
        return {transaction.account_id: -(montant + frais)}
    if type_ in TransactionType.income_values():
        return {transaction.account_id: montant - frais}
    if (
        type_ in TransactionType.transfer_values()
        and transaction.destination_account_id
        and transaction.destination_account_id != transaction.account_id
    ):
        return {
            transaction.account_id: -(montant + frais),
            transaction.destination_account_id: montant,
        }
    return {}


class TransactionService:
    """Service pour la gestion des transactions financières."""

    @staticmethod
    def create_transaction(
        user_id: int,
        account_id: int,
        amount: Decimal,
        transaction_type: str,
        description: str,
        transaction_date: date = None,  # Paramètre historique (date seulement)
        transaction_datetime: datetime = None,  # Nouveau paramètre (date + heure)
        category_id: int = None,
        destination_account_id: int = None,
        fees: Decimal = Decimal("0.00"),
        notes: str = None,
        status: str = "completed",
        commit: bool = True,
        verifier_solde: bool = True,
    ) -> Transaction:
        """
        Crée une nouvelle transaction financière.

        Args:
            user_id: ID de l'utilisateur effectuant la transaction
            account_id: ID du compte source
            amount: Montant de la transaction (toujours positif)
            transaction_type: Type de transaction (défini dans TransactionType)
            description: Description de la transaction
            transaction_date: Date de la transaction (par défaut: aujourd'hui)
            category_id: ID de la catégorie (optionnel)
            destination_account_id: ID du compte destination (pour les virements)
            fees: Frais de transaction (par défaut: 0.00)
            notes: Notes internes (optionnel)
            status: Statut de la transaction (par défaut: 'completed')
            commit: Si False, flush sans commit et sans notifications
                (pour les imports en lot atomiques — l'appelant gère
                le commit/rollback final)
            verifier_solde: Si False, accepte un débit qui dépasse le solde
                et le découvert autorisé (import de relevé bancaire)

        Returns:
            Transaction: L'objet Transaction créé

        Raises:
            AccountNotFoundError: Si le compte source n'existe pas
            CategoryNotFoundError: Si la catégorie spécifiée n'existe pas
            InsufficientFundsError: Si le solde est insuffisant pour une dépense
            InvalidTransactionError: Si la transaction est invalide
        """
        # Validation des entrées
        if amount <= 0:
            raise InvalidTransactionError("Le montant doit être supérieur à zéro")

        # Déterminer la date/heure de la transaction
        if transaction_datetime:
            # Utiliser la date/heure fournie
            final_datetime = transaction_datetime
            final_date = transaction_datetime.date()
        elif transaction_date:
            # Convertir la date en datetime (midi par défaut)
            final_datetime = datetime.combine(
                transaction_date, datetime.min.time().replace(hour=12)
            )
            final_date = transaction_date
        else:
            # Par défaut: maintenant
            final_datetime = datetime.now()
            final_date = final_datetime.date()

        # Vérification de l'existence du compte source
        account = (
            Account.query.filter_by(id=account_id, user_id=user_id)
            .with_for_update()
            .first()
        )

        if not account:
            raise AccountNotFoundError("Le compte source spécifié n'existe pas")

        # Vérification de la catégorie si spécifiée
        category = None
        if category_id is not None:
            category = Category.query.filter_by(id=category_id, user_id=user_id).first()

            if not category:
                raise CategoryNotFoundError("La catégorie spécifiée n'existe pas")

        # Vérification du compte destination pour les virements
        destination_account = None
        if destination_account_id:
            destination_account = (
                Account.query.filter_by(id=destination_account_id, user_id=user_id)
                .with_for_update()
                .first()
            )

            if not destination_account:
                raise AccountNotFoundError(
                    "Le compte destination spécifié n'existe pas"
                )
            if destination_account_id == account_id:
                raise InvalidTransactionError(
                    "Le compte destination doit être différent du compte source"
                )

        is_transfer = (
            transaction_type in TransactionType.transfer_values()
            and destination_account is not None
        )

        # Vérification du solde pour les dépenses et les virements (débit du compte source).
        # Désactivée pour l'import d'un relevé : la banque a déjà passé l'opération,
        # même si elle a mis le compte à découvert sans autorisation.
        if verifier_solde and (
            transaction_type in TransactionType.expense_values() or is_transfer
        ):
            if not account.peut_debiter(amount + fees):
                raise InsufficientFundsError(
                    "Solde insuffisant pour effectuer cette opération"
                )

        # Création de la transaction
        transaction = Transaction(
            user_id=user_id,
            account_id=account_id,
            destination_account_id=destination_account_id,
            category_id=category_id,
            montant=amount,
            frais_transaction=fees,
            type_transaction=transaction_type,
            libelle=description,
            date_heure_transaction=final_datetime,  # Utiliser date+heure complète
            date_valeur=final_date,  # Date seulement pour compatibilité
            notes=notes,
            statut=status,
        )

        # Mise à jour des soldes des comptes
        if status == "completed":
            logger.info(
                f"🔄 Mise à jour des soldes - Type: {transaction_type}, Montant: {amount}, Frais: {fees}"
            )
            expense_types = TransactionType.expense_values()
            income_types = TransactionType.income_values()
            logger.info(f"📋 Types dépenses: {expense_types}")
            logger.info(f"📋 Types revenus: {income_types}")

            if transaction_type in expense_types:
                logger.info(f"💸 Dépense détectée - Mise à jour compte {account_id}")
                # Mise à jour directe en base de données
                db.session.execute(
                    db.text(
                        'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel - :amount WHERE id_compte = :account_id'
                    ),
                    {"amount": float(amount + fees), "account_id": account_id},
                )
                logger.info("✅ Requête UPDATE exécutée pour dépense")
            elif transaction_type in income_types:
                logger.info(f"💰 Revenu détecté - Mise à jour compte {account_id}")
                # Mise à jour directe en base de données
                db.session.execute(
                    db.text(
                        'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel + :amount WHERE id_compte = :account_id'
                    ),
                    {"amount": float(amount - fees), "account_id": account_id},
                )
                logger.info("✅ Requête UPDATE exécutée pour revenu")
            elif is_transfer:
                logger.info(
                    f"🔄 Virement détecté - Comptes {account_id} → {destination_account_id}"
                )
                # Mise à jour du compte source
                db.session.execute(
                    db.text(
                        'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel - :amount WHERE id_compte = :account_id'
                    ),
                    {"amount": float(amount + fees), "account_id": account_id},
                )
                # Mise à jour du compte destination
                db.session.execute(
                    db.text(
                        'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel + :amount WHERE id_compte = :account_id'
                    ),
                    {"amount": float(amount), "account_id": destination_account_id},
                )
                logger.info("✅ Requêtes UPDATE exécutées pour virement")
            else:
                logger.warning(
                    f"⚠️ Type de transaction non reconnu: {transaction_type}"
                )
            db.session.flush()
        else:
            logger.info(
                f"⏸️ Transaction non complétée (statut: {status}) - pas de mise à jour des soldes"
            )

        db.session.add(transaction)

        # Mode import en lot : flush sans commit, pas de notifications
        # (l'appelant committera ou annulera l'ensemble)
        if not commit:
            db.session.flush()
            # Expirer les instances pour que les vérifications de solde
            # des lignes suivantes relisent les soldes mis à jour en SQL brut
            db.session.expire_all()
            return transaction

        db.session.commit()

        # 📧 Envoi de notification email après création de transaction
        try:
            logger.info(
                f"🔔 Envoi notification transaction pour user_id={user_id}, amount={amount}"
            )
            from core.services.notifications import NotificationService

            NotificationService.send_notification(
                user_id=user_id,
                title="Nouvelle transaction enregistrée",
                message=f"Transaction de {amount}€ dans la catégorie {category.name if category else 'Non catégorisée'}",
                notification_type="general_email",
                send_email=True,
                force_send=True,
            )
            logger.info("✅ Notification transaction envoyée avec succès")
        except Exception as e:
            # Ne pas faire échouer la transaction si l'email échoue
            logger.warning(f"❌ Erreur envoi notification transaction: {e}")
            import traceback

            logger.warning(f"Traceback: {traceback.format_exc()}")

        # 🚨 Vérifier si le solde du compte est devenu faible après la transaction
        try:
            from core.services.accounts.account_services import AccountService

            updated_account = AccountService.get_account(account_id, user_id)
            AccountService._check_low_balance_alert(updated_account, user_id)
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification d'alerte solde faible: {e}")

        # Vérifier les dépassements de budget après chaque transaction
        try:
            from core.services.budgets.budget_services import check_budget_notifications

            check_budget_notifications(user_id)
        except Exception as e:
            logger.warning(f"Erreur vérification budget post-transaction: {e}")

        return transaction

    @staticmethod
    def get_transaction(transaction_id: int, user_id: int) -> Optional[Transaction]:
        """
        Récupère une transaction par son ID en vérifiant les permissions.

        Args:
            transaction_id: ID de la transaction à récupérer
            user_id: ID de l'utilisateur effectuant la requête

        Returns:
            Optional[Transaction]: La transaction trouvée ou None si non trouvée

        Raises:
            TransactionNotFoundError: Si la transaction n'existe pas
            DatabaseError: En cas d'erreur de base de données
        """
        try:
            transaction = Transaction.query.filter_by(
                id=transaction_id, user_id=user_id
            ).first()

            if not transaction:
                raise TransactionNotFoundError("La transaction spécifiée n'existe pas")

            return transaction

        except SQLAlchemyError as e:
            raise DatabaseError(
                f"Erreur lors de la récupération de la transaction: {str(e)}"
            ) from e

    @classmethod
    def delete_transaction(cls, transaction_id: int, user_id: int) -> bool:
        """
        Supprime une transaction en vérifiant les permissions.

        Args:
            transaction_id: ID de la transaction à supprimer
            user_id: ID de l'utilisateur effectuant la requête

        Returns:
            bool: True si la suppression a réussi

        Raises:
            TransactionNotFoundError: Si la transaction n'existe pas
            DatabaseError: En cas d'erreur de base de données
        """
        try:
            transaction = cls.get_transaction(transaction_id, user_id)

            # Sauvegarder les infos pour notification
            transaction_libelle = transaction.libelle
            transaction_montant = transaction.montant
            transaction_type = transaction.type_transaction

            # Vérification des contraintes métier (ex: transaction déjà validée)
            if transaction.statut == "completed":
                # Mêmes listes que create_transaction (types historiques inclus),
                # sinon la suppression n'annule pas ce que la création a appliqué
                expense_types = TransactionType.expense_values()
                income_types = TransactionType.income_values()

                # Annulation de la transaction (inverse des opérations via SQL UPDATE)
                if transaction.type_transaction in expense_types:
                    # Pour une dépense, on crédite le compte
                    db.session.execute(
                        db.text(
                            'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel + :amount WHERE id_compte = :account_id'
                        ),
                        {
                            "amount": float(
                                transaction.montant + transaction.frais_transaction
                            ),
                            "account_id": transaction.account_id,
                        },
                    )
                elif transaction.type_transaction in income_types:
                    # Pour un revenu, on débite ce que la création a crédité (montant - frais)
                    db.session.execute(
                        db.text(
                            'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel - :amount WHERE id_compte = :account_id'
                        ),
                        {
                            "amount": float(
                                transaction.montant
                                - (transaction.frais_transaction or 0)
                            ),
                            "account_id": transaction.account_id,
                        },
                    )
                elif (
                    transaction.type_transaction in TransactionType.transfer_values()
                    and transaction.destination_account
                ):
                    # Pour un virement, on inverse les opérations
                    db.session.execute(
                        db.text(
                            'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel + :amount WHERE id_compte = :account_id'
                        ),
                        {
                            "amount": float(
                                transaction.montant + transaction.frais_transaction
                            ),
                            "account_id": transaction.account_id,
                        },
                    )
                    db.session.execute(
                        db.text(
                            'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel - :amount WHERE id_compte = :account_id'
                        ),
                        {
                            "amount": float(transaction.montant),
                            "account_id": transaction.destination_account.id,
                        },
                    )
                db.session.flush()

            # Suppression de la transaction
            db.session.delete(transaction)
            db.session.commit()

            # 📧 Notification de suppression de transaction
            try:
                from core.services.notifications import NotificationService

                NotificationService.send_notification(
                    user_id=user_id,
                    title="Transaction supprimée",
                    message=f"Transaction '{transaction_libelle}' de {transaction_montant}€ supprimée",
                    notification_type="transaction_deleted",
                    action_url="/transactions/",
                    send_email=True,
                    metadata={
                        "transaction_libelle": transaction_libelle,
                        "transaction_montant": float(transaction_montant),
                        "transaction_type": transaction_type,
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Erreur envoi notification suppression transaction: {e}"
                )

            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            raise DatabaseError(
                f"Erreur lors de la suppression de la transaction: {str(e)}"
            ) from e

    @staticmethod
    def get_transactions(
        user_id: int,
        start_date: date = None,
        end_date: date = None,
        account_id: int = None,
        category_id: int = None,
        transaction_type: str = None,
        min_amount: Decimal = None,
        max_amount: Decimal = None,
        status: str = None,
        search: str = None,
        page: int = 1,
        per_page: int = 20,
        **kwargs,
    ) -> Tuple[List[Transaction], int]:
        """
        Récupère les transactions selon les critères de filtrage.

        Args:
            user_id: ID de l'utilisateur
            start_date: Date de début (inclusive)
            end_date: Date de fin (inclusive)
            account_id: Filtrer par compte
            category_id: Filtrer par catégorie
            transaction_type: Type de transaction
            min_amount: Montant minimum
            max_amount: Montant maximum
            status: Statut de la transaction
            search: Recherche dans la description
            page: Numéro de page
            per_page: Nombre d'éléments par page

        Returns:
            Tuple[List[Transaction], int]: Liste des transactions et nombre total
        """
        query = Transaction.query.filter_by(user_id=user_id)

        # Filtres
        if start_date:
            query = query.filter(Transaction.date_heure_transaction >= start_date)
        if end_date:
            # Une date seule couvre toute la journée (sinon <= minuit l'exclut)
            if not isinstance(end_date, datetime):
                query = query.filter(
                    Transaction.date_heure_transaction < end_date + timedelta(days=1)
                )
            else:
                query = query.filter(Transaction.date_heure_transaction <= end_date)
        if account_id:
            query = query.filter(
                or_(
                    Transaction.account_id == account_id,
                    Transaction.destination_account_id == account_id,
                )
            )
        if category_id:
            query = query.filter(Transaction.category_id == category_id)
        if transaction_type:
            query = query.filter(Transaction.type_transaction == transaction_type)

        # Gestion des types multiples (pour gérer les incohérences de casse)
        transaction_types = kwargs.get("transaction_types")
        if transaction_types:
            query = query.filter(Transaction.type_transaction.in_(transaction_types))
        if min_amount is not None:
            query = query.filter(Transaction.montant >= min_amount)
        if max_amount is not None:
            query = query.filter(Transaction.montant <= max_amount)
        if status:
            query = query.filter(Transaction.statut == status)
        if search:
            search_term = f"%{search}%"
            query = query.filter(Transaction.libelle.ilike(search_term))

        # Tri par défaut: date décroissante
        query = query.order_by(
            Transaction.date_heure_transaction.desc(), Transaction.id.desc()
        )

        # Pagination
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return pagination.items, pagination.total

    @staticmethod
    def get_transaction_summary(
        user_id: int,
        start_date: date,
        end_date: date,
        group_by: str = "category",  # 'category', 'type', 'account', 'day', 'month'
    ) -> List[Dict]:
        """
        Génère un résumé des transactions selon le critère de regroupement.

        Args:
            user_id: ID de l'utilisateur
            start_date: Date de début
            end_date: Date de fin
            group_by: Critère de regroupement

        Returns:
            List[Dict]: Liste des résumés avec montants agrégés
        """
        # Base de la requête
        query = db.session.query(
            func.sum(Transaction.montant).label("total_amount"),
            func.count(Transaction.id).label("transaction_count"),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.date_heure_transaction.between(start_date, end_date),
            Transaction.statut == "completed",
        )

        # Ajout du groupement
        if group_by == "category":
            query = query.join(Category).group_by(
                Transaction.category_id, Category.name
            )
            query = query.add_columns(Category.name.label("group_name"))
        elif group_by == "type":
            query = query.group_by(Transaction.transaction_type)
            query = query.add_columns(Transaction.transaction_type.label("group_name"))
        elif group_by == "account":
            query = query.join(Account, Transaction.account_id == Account.id)
            query = query.group_by(Transaction.account_id, Account.name)
            query = query.add_columns(Account.name.label("group_name"))
        elif group_by == "day":
            query = query.add_columns(
                extract("day", Transaction.date_heure_transaction).label("day"),
                extract("month", Transaction.date_heure_transaction).label("month"),
                extract("year", Transaction.date_heure_transaction).label("year"),
            )
            query = query.group_by("day", "month", "year")
        elif group_by == "month":
            query = query.add_columns(
                extract("month", Transaction.date_heure_transaction).label("month"),
                extract("year", Transaction.date_heure_transaction).label("year"),
            )
            query = query.group_by("month", "year")

        # Exécution de la requête
        results = query.all()

        # Formatage des résultats
        summary = []
        for row in results:
            if group_by in ["day", "month"]:
                group_name = (
                    f"{int(row.day or 1)}/{int(row.month)}/{int(row.year)}"
                    if group_by == "day"
                    else f"{int(row.month)}/{int(row.year)}"
                )
            else:
                group_name = row.group_name or "Non catégorisé"

            summary.append(
                {
                    "group": group_name,
                    "total_amount": float(row.total_amount or 0),
                    "transaction_count": row.transaction_count,
                }
            )

        return summary

    @staticmethod
    def get_user_accounts(user_id: int) -> List[Account]:
        """
        Récupère les comptes actifs d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur

        Returns:
            List[Account]: Liste des comptes actifs de l'utilisateur
        """
        try:
            return (
                Account.query.filter(
                    Account.user_id == user_id, Account._is_active_db == True
                )
                .order_by(Account.name)
                .all()
            )
        except Exception as e:
            logger.error(
                f"Erreur récupération comptes user {user_id}: {e}", exc_info=True
            )
            return []

    @staticmethod
    def get_user_categories(user_id: int) -> List[Category]:
        """
        Récupère les catégories d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur

        Returns:
            List[Category]: Liste des catégories de l'utilisateur
        """
        try:
            return (
                Category.query.filter_by(user_id=user_id).order_by(Category.name).all()
            )
        except Exception as e:
            logger.error(
                f"Erreur récupération catégories user {user_id}: {e}", exc_info=True
            )
            return []

    @staticmethod
    def get_user_transactions(user_id: int, page: int = 1, per_page: int = 10):
        """
        Récupère les transactions paginées d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            page: Numéro de page
            per_page: Nombre d'éléments par page

        Returns:
            Dict: Dictionnaire avec 'items' et 'pagination'
        """
        try:
            from core.models.transactions import Transaction

            pagination = (
                Transaction.query.filter_by(user_id=user_id)
                .order_by(
                    Transaction.date_heure_transaction.desc(), Transaction.id.desc()
                )
                .paginate(page=page, per_page=per_page, error_out=False)
            )

            return {"items": pagination.items, "pagination": pagination}
        except Exception as e:
            logger.error(
                f"Erreur récupération transactions user {user_id}: {e}", exc_info=True
            )
            return {"items": [], "pagination": None}

    @staticmethod
    def get_transaction_by_id(transaction_id: int, user_id: int):
        """
        Récupérer une transaction par son ID pour un utilisateur donné.

        Args:
            transaction_id (int): ID de la transaction
            user_id (int): ID de l'utilisateur

        Returns:
            Transaction: La transaction trouvée ou None
        """
        try:
            return Transaction.query.filter_by(
                id=transaction_id, user_id=user_id
            ).first()
        except Exception as e:
            logger.error(
                f"Erreur lors de la récupération de la transaction {transaction_id}: {e}"
            )
            return None

    @staticmethod
    def update_transaction(transaction_id: int, user_id: int, **update_data):
        """
        Mettre à jour une transaction.

        Args:
            transaction_id (int): ID de la transaction
            user_id (int): ID de l'utilisateur
            **update_data: Données à mettre à jour

        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            transaction = Transaction.query.filter_by(
                id=transaction_id, user_id=user_id
            ).first()

            if not transaction:
                return False

            # Sauvegarder les anciennes valeurs pour la notification
            old_values = {}
            changes = []

            # Effet sur les soldes AVANT modification (pour réconcilier ensuite)
            effets_avant = effets_sur_soldes(transaction)

            # Mettre à jour les champs et détecter les changements
            for field, value in update_data.items():
                if hasattr(transaction, field):
                    old_value = getattr(transaction, field)
                    if old_value != value:
                        old_values[field] = old_value
                        setattr(transaction, field, value)

                        # Formatage des changements pour la notification
                        field_labels = {
                            "montant": "montant",
                            "date_heure_transaction": "date",
                            "libelle": "libellé",
                            "type_transaction": "type",
                            "category_id": "catégorie",
                        }
                        field_label = field_labels.get(field, field)

                        if field == "date_heure_transaction":
                            old_date = (
                                old_value.strftime("%d/%m/%Y") if old_value else "N/A"
                            )
                            new_date = value.strftime("%d/%m/%Y") if value else "N/A"
                            changes.append(f"{field_label}: {old_date} → {new_date}")
                        elif field == "montant":
                            changes.append(f"{field_label}: {old_value}€ → {value}€")
                        else:
                            changes.append(f"{field_label}: '{old_value}' → '{value}'")

            if changes:  # Seulement si il y a des changements
                transaction.date_mise_a_jour = datetime.now(timezone.utc)

                # 💰 Réconciliation : appliquer (effet nouveau - effet ancien) à chaque
                # compte touché ; couvre montant, frais, type (y compris dépense <->
                # virement), changement de compte ou de destination, et statut
                effets_apres = effets_sur_soldes(transaction)
                for compte_id in set(effets_avant) | set(effets_apres):
                    delta = effets_apres.get(
                        compte_id, Decimal("0")
                    ) - effets_avant.get(compte_id, Decimal("0"))
                    if delta:
                        db.session.execute(
                            db.text(
                                'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel + :delta WHERE id_compte = :account_id'
                            ),
                            {"delta": delta, "account_id": compte_id},
                        )
                db.session.flush()

                db.session.commit()

                # 📧 Notification de modification de transaction
                try:
                    from core.services.notifications import NotificationService

                    NotificationService.send_notification(
                        user_id=user_id,
                        title="Transaction modifiée",
                        message=f"La transaction '{transaction.libelle}' a été modifiée: {', '.join(changes)}",
                        notification_type="transaction_updated",
                        action_url=f"/transactions/{transaction.id}",
                        send_email=True,
                        metadata={
                            "transaction_id": transaction.id,
                            "transaction_title": transaction.libelle,
                            "changes": changes,
                        },
                    )
                except Exception as e:
                    logger.warning(
                        f"Erreur envoi notification modification transaction: {e}"
                    )

                return True
            else:
                # Pas de changements détectés
                return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Erreur lors de la mise à jour de la transaction {transaction_id}: {e}"
            )
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erreur inattendue lors de la mise à jour: {e}")
            return False
