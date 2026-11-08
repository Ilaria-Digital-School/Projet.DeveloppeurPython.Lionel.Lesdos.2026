"""
Services pour la gestion des comptes bancaires.

Ce module contient la logique métier pour les opérations sur les comptes bancaires.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.extensions import db
from core.models.account import Account
from core.schemas.account import (
    AccountCreate,
    AccountUpdate,
)
from shared.exceptions import (
    ConflictError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)


class AccountService:
    """
    Service pour la gestion des comptes bancaires.

    Ce service gère les opérations CRUD sur les comptes bancaires, ainsi que
    les opérations spécifiques comme les transferts et les mises à jour de solde.
    """

    LOW_BALANCE_THRESHOLDS = {
        "checking": 100.0,
        "savings": 500.0,
        "credit": 200.0,
        "investment": 1000.0,
    }
    DEFAULT_THRESHOLD = 50.0

    @classmethod
    def create_account(cls, user_id: int, account_data: Dict[str, Any]) -> Account:
        """
        Crée un nouveau compte bancaire.

        Args:
            user_id: ID de l'utilisateur propriétaire du compte
            account_data: Données du compte à créer

        Returns:
            Account: Le compte créé

        Raises:
            ValidationError: Si les données du compte sont invalides
            DatabaseError: En cas d'erreur de base de données
            ConflictError: Si un compte avec les mêmes données existe déjà
        """
        try:
            # Validation des données avec Pydantic
            account_create = AccountCreate(**account_data)

            # Vérifier si l'utilisateur a déjà un compte avec le même nom
            existing_account = Account.query.filter_by(
                user_id=user_id, name=account_create.name
            ).first()

            if existing_account:
                raise ConflictError(
                    f"Un compte avec le nom '{account_create.name}' existe déjà"
                )

            # Création du compte
            account = Account(
                user_id=user_id,
                name=account_create.name,
                account_type=account_create.account_type,
                balance=account_create.initial_balance,
                overdraft_limit=account_create.overdraft_limit,
                currency=account_create.currency,
                bank_name=account_create.bank_name,
                account_number=account_create.account_number,
                iban=account_create.iban,
                bic_swift=account_create.bic_swift,
                is_active=account_create.is_active,
                notes=account_create.notes,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            db.session.add(account)
            db.session.commit()

            # 📧 Notification de création de compte
            try:
                from core.services.notifications import NotificationService

                NotificationService.send_notification(
                    user_id=user_id,
                    title="Nouveau compte créé",
                    message=f"Le compte '{account.name}' a été créé avec succès (Solde initial: {account.balance}€)",
                    notification_type="account_created",
                    action_url=f"/comptes/{account.id}",
                    send_email=True,
                    metadata={
                        "account_id": account.id,
                        "account_name": account.name,
                        "account_type": account.account_type,
                        "initial_balance": float(account.balance),
                    },
                )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Erreur envoi notification création compte: {e}")

            return account

        except PydanticValidationError as e:
            raise ValidationError(
                f"Données de compte invalides: {str(e)}",
                field_errors={"validation": str(e)},
            )
        except IntegrityError as e:
            db.session.rollback()
            if "duplicate key" in str(e).lower():
                raise ConflictError("Un compte avec ces informations existe déjà")
            raise DatabaseError("Erreur lors de la création du compte")
        except SQLAlchemyError:
            db.session.rollback()
            raise DatabaseError("Erreur de base de données")

    @classmethod
    def get_account(cls, account_id: int, user_id: int) -> Account:
        """
        Récupère un compte par son ID.

        Args:
            account_id: ID du compte à récupérer
            user_id: ID de l'utilisateur propriétaire

        Returns:
            Account: Le compte trouvé

        Raises:
            NotFoundError: Si le compte n'existe pas ou n'appartient pas à l'utilisateur
            DatabaseError: En cas d'erreur de base de données
        """
        try:
            account = Account.query.filter_by(id=account_id, user_id=user_id).first()
            if not account:
                raise NotFoundError(
                    f"Compte avec l'ID {account_id} non trouvé ou accès non autorisé"
                )
            return account

        except SQLAlchemyError:
            raise DatabaseError("Erreur lors de la récupération du compte")

    @classmethod
    def list_accounts(
        cls, user_id: int, active_only: bool = True, account_type: Optional[str] = None
    ) -> List[Account]:
        """
        Liste les comptes d'un utilisateur avec des filtres optionnels.

        Args:
            user_id: ID de l'utilisateur
            active_only: Si True, ne retourne que les comptes actifs
            account_type: Filtre optionnel sur le type de compte

        Returns:
            List[Account]: Liste des comptes correspondant aux critères

        Raises:
            DatabaseError: En cas d'erreur de base de données
        """
        try:
            query = Account.query.filter_by(user_id=user_id)

            if active_only:
                query = query.filter(Account._is_active_db == True)

            if account_type:
                query = query.filter(Account._account_type_db == account_type)

            return query.order_by(Account.name).all()

        except SQLAlchemyError:
            raise DatabaseError("Erreur lors de la récupération des comptes")

    @classmethod
    def update_account(
        cls, account_id: int, user_id: int, update_data: Dict[str, Any]
    ) -> Account:
        """
        Met à jour un compte existant.

        Args:
            account_id: ID du compte à mettre à jour
            user_id: ID de l'utilisateur propriétaire
            update_data: Données à mettre à jour

        Returns:
            Account: Le compte mis à jour

        Raises:
            NotFoundError: Si le compte n'existe pas ou n'appartient pas à l'utilisateur
            ValidationError: Si les données de mise à jour sont invalides
            ConflictError: Si la mise à jour crée un conflit (ex: nom de compte dupliqué)
            DatabaseError: En cas d'erreur de base de données
        """
        try:
            # Valider les données de mise à jour avec Pydantic
            # On utilise dict pour ignorer les champs None
            update_data_filtered = {
                k: v for k, v in update_data.items() if v is not None
            }
            account_update = AccountUpdate(**update_data_filtered)

            # Récupérer le compte
            account = cls.get_account(account_id, user_id)

            # Sauvegarder les anciennes valeurs pour la notification
            old_name = account.name
            old_balance = account.balance

            # Vérifier les conflits de noms si le nom est mis à jour
            if account_update.name and account_update.name != account.name:
                existing_account = Account.query.filter(
                    Account.id != account_id,
                    Account.user_id == user_id,
                    Account.name == account_update.name,
                ).first()

                if existing_account:
                    raise ConflictError(
                        f"Un compte avec le nom '{account_update.name}' existe déjà"
                    )

            # Mise à jour des champs
            for field, value in account_update.model_dump(exclude_unset=True).items():
                if field == "balance":
                    # Saisie manuelle : garde solde_actuel = initial + transactions
                    account.ajuster_solde(value)
                else:
                    setattr(account, field, value)

            account.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            # 📧 Notification de modification de compte
            try:
                from core.services.notifications import NotificationService

                changes = []

                # Détecter tous les changements possibles
                if (
                    hasattr(account_update, "name")
                    and account_update.name
                    and account_update.name != old_name
                ):
                    changes.append(f"nom: '{old_name}' → '{account.name}'")

                if (
                    hasattr(account_update, "balance")
                    and account_update.balance is not None
                    and account_update.balance != old_balance
                ):
                    changes.append(f"solde: {old_balance}€ → {account.balance}€")

                # Autres champs modifiables
                if hasattr(account_update, "dict"):
                    update_dict = account_update.model_dump(exclude_unset=True)
                    for field_name, new_value in update_dict.items():
                        if field_name not in ["name", "balance"]:  # Déjà traités
                            old_value = getattr(account, field_name, None)
                            if new_value != old_value:
                                field_label = {
                                    "account_type": "type",
                                    "currency": "devise",
                                    "bank_name": "nom de banque",
                                    "account_number": "numéro de compte",
                                    "iban": "IBAN",
                                    "bic_swift": "BIC",
                                    "is_active": "statut",
                                }.get(field_name, field_name)

                                if field_name == "is_active":
                                    old_status = "actif" if old_value else "inactif"
                                    new_status = "actif" if new_value else "inactif"
                                    changes.append(
                                        f"{field_label}: {old_status} → {new_status}"
                                    )
                                else:
                                    changes.append(
                                        f"{field_label}: '{old_value}' → '{new_value}'"
                                    )

                # Toujours envoyer une notification de modification
                NotificationService.send_notification(
                    user_id=user_id,
                    title="Compte modifié",
                    message=f"Le compte '{account.name}' a été modifié"
                    + (f": {', '.join(changes)}" if changes else " avec succès"),
                    notification_type="account_updated",
                    action_url=f"/comptes/{account.id}",
                    send_email=True,
                    metadata={
                        "account_id": account.id,
                        "account_name": account.name,
                        "changes": changes,
                    },
                )

            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Erreur envoi notification modification compte: {e}")

            return account

        except PydanticValidationError as e:
            raise ValidationError(
                f"Données de mise à jour invalides: {str(e)}",
                field_errors={"validation": str(e)},
            )
        except IntegrityError as e:
            db.session.rollback()
            if "duplicate key" in str(e).lower():
                raise ConflictError(
                    "La mise à jour crée un conflit avec un compte existant"
                )
            raise DatabaseError("Erreur lors de la mise à jour du compte")
        except SQLAlchemyError:
            db.session.rollback()
            raise DatabaseError(
                "Erreur de base de données lors de la mise à jour du compte"
            )

    @classmethod
    def delete_account(cls, account_id: int, user_id: int) -> bool:
        """
        Supprime un compte de manière sécurisée.

        Si le compte a des transactions associées, il est marqué comme inactif
        au lieu d'être supprimé pour préserver l'historique.

        Args:
            account_id: ID du compte à supprimer
            user_id: ID de l'utilisateur propriétaire

        Returns:
            bool: True si la suppression a réussi

        Raises:
            NotFoundError: Si le compte n'existe pas ou n'appartient pas à l'utilisateur
            DatabaseError: En cas d'erreur de base de données
        """
        try:
            # Vérifier que le compte existe et appartient à l'utilisateur
            account = cls.get_account(account_id, user_id)

            # Sauvegarder les infos pour la notification
            account_name = account.name
            account_type = account.account_type
            account_balance = account.balance

            # Supprimer le compte directement
            db.session.delete(account)
            db.session.commit()

            # 📧 Notification de suppression de compte
            try:
                from core.services.notifications import NotificationService

                NotificationService.send_notification(
                    user_id=user_id,
                    title="Compte supprimé",
                    message=f"Le compte '{account_name}' ({account_type}) a été supprimé avec succès",
                    notification_type="account_deleted",
                    action_url="/comptes/",
                    send_email=True,
                    metadata={
                        "account_name": account_name,
                        "account_type": account_type,
                        "final_balance": float(account_balance),
                    },
                )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Erreur envoi notification suppression compte: {e}")

            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            raise DatabaseError(f"Erreur lors de la suppression du compte: {str(e)}")

    @classmethod
    def _calculate_account_stats(cls, account: Account) -> Dict[str, Any]:
        """
        Calcule les statistiques d'un compte.

        Args:
            account: Instance du compte

        Returns:
            Dict: Dictionnaire contenant les statistiques
        """
        # Implémentation simplifiée - à compléter avec la logique métier
        return {
            "transaction_count": 0,  # À implémenter
            "monthly_average": 0.0,  # À implémenter
            "last_transaction_date": None,  # À implémenter
        }

    @classmethod
    def _check_low_balance_alert(cls, account: Account, user_id: int) -> None:
        """
        Vérifie si le solde d'un compte est faible et envoie une alerte si nécessaire.

        Args:
            account: Instance du compte à vérifier
            user_id: ID de l'utilisateur propriétaire
        """
        try:
            threshold = cls.LOW_BALANCE_THRESHOLDS.get(
                account.account_type, cls.DEFAULT_THRESHOLD
            )

            # Vérifier si le solde est en dessous du seuil ET positif
            if 0 < account.balance < threshold:
                from core.services.notifications import NotificationService

                # Calculer le pourcentage par rapport au seuil
                percentage = (account.balance / threshold) * 100

                NotificationService.send_notification(
                    user_id=user_id,
                    title=f"⚠️ Solde faible - {account.name}",
                    message=f"Le solde de votre compte '{account.name}' est faible: {account.balance:.2f}€ (seuil: {threshold:.0f}€)",
                    notification_type="account_balance_low",
                    action_url=f"/comptes/{account.id}",
                    send_email=True,
                    metadata={
                        "account_id": account.id,
                        "account_name": account.name,
                        "current_balance": float(account.balance),
                        "threshold": threshold,
                        "percentage_of_threshold": round(percentage, 2),
                        "account_type": account.account_type,
                    },
                )
                import logging

                logger = logging.getLogger(__name__)
                logger.info(
                    f"🚨 Alerte solde faible envoyée pour compte {account.name}: {account.balance:.2f}€"
                )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Erreur lors de la vérification d'alerte solde faible: {e}")


# Instance globale du service pour compatibilité
account_service = AccountService()
