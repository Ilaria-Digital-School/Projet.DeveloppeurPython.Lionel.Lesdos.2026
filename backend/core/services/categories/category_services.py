"""
Services pour la gestion des catégories.

Ce module contient la logique métier pour la gestion des catégories,
y compris la création, la lecture, la mise à jour et la suppression
de catégories de transactions.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import lazyload

from core.extensions import db
from core.models.category import Category

from .exceptions import (
    CategoryError,
    CategoryIntegrityError,
    CategoryNotFoundError,
    CategoryPermissionError,
    CategoryValidationError,
)


class CategoryService:
    """
    Service pour la gestion des opérations sur les catégories.

    Ce service encapsule toute la logique métier liée aux catégories,
    y compris la validation des données, l'autorisation d'accès et
    les interactions avec la base de données.
    """

    @classmethod
    def get_user_categories(
        cls,
        user_id: int,
        include_global: bool = True,
        with_transactions: bool = False,
        is_expense: Optional[bool] = None,
    ) -> List[Category]:
        """
        Récupère les catégories d'un utilisateur.

        Args:
            user_id: Identifiant unique de l'utilisateur
            include_global: Si True, inclut les catégories globales (sans utilisateur)
            with_transactions: Si True, charge également les transactions associées
            is_expense: Si spécifié, filtre par type de catégorie (dépense/revenu)

        Returns:
            List[Category]: Liste des catégories de l'utilisateur

        Raises:
            CategoryError: Si une erreur inattendue se produit
            DatabaseError: En cas d'erreur d'accès à la base de données
        """
        try:
            query = Category.query

            # Filtre par utilisateur et/ou catégories globales
            if include_global:
                query = query.filter(
                    (Category.user_id == user_id) | (Category.user_id.is_(None))
                )
            else:
                query = query.filter_by(user_id=user_id)

            # Filtre par type de catégorie si spécifié
            if is_expense is not None:
                query = query.filter_by(is_expense=is_expense)

            # Option pour charger les transactions
            if with_transactions:
                query = query.options(lazyload(Category.transactions))

            # Tri par nom de catégorie
            return query.order_by(Category.name.asc()).all()

        except SQLAlchemyError as e:
            raise CategoryError(
                f"Erreur lors de la récupération des catégories: {str(e)}"
            ) from e

    @classmethod
    def get_category(
        cls,
        category_id: int,
        user_id: int,
        with_transactions: bool = False,
        allow_global: bool = True,
    ) -> Category:
        """
        Récupère une catégorie par son ID en vérifiant les permissions.

        Args:
            category_id: Identifiant unique de la catégorie
            user_id: Identifiant de l'utilisateur effectuant la requête
            with_transactions: Si True, charge également les transactions associées
            allow_global: Si True, autorise l'accès aux catégories globales

        Returns:
            Category: L'objet Category demandé

        Raises:
            CategoryNotFoundError: Si la catégorie n'existe pas
            CategoryPermissionError: Si l'utilisateur n'a pas les droits sur cette catégorie
            CategoryError: Pour toutes les autres erreurs

        Example:
            >>> category = CategoryService.get_category(1, 1)
            >>> category.name
            'Alimentation'
        """
        try:
            # Chargement avec option de chargement paresseux
            options = []
            if not with_transactions:
                options.append(lazyload(Category.transactions))

            category = db.session.get(Category, category_id, options=options)

            if not category:
                raise CategoryNotFoundError(
                    f"Aucune catégorie trouvée avec l'ID {category_id}"
                )

            # Vérification des permissions
            if category.user_id is None:
                if not allow_global:
                    raise CategoryPermissionError(
                        "L'accès aux catégories globales n'est pas autorisé"
                    )
            elif category.user_id != user_id:
                raise CategoryPermissionError(
                    f"Vous n'avez pas l'autorisation d'accéder à cette catégorie"
                )

            return category

        except SQLAlchemyError as e:
            raise CategoryError(
                f"Erreur lors de la récupération de la catégorie: {str(e)}"
            ) from e

    @staticmethod
    def _is_valid_hex_color(color: str) -> bool:
        """
        Vérifie si une chaîne est une couleur hexadécimale valide.

        Args:
            color: La couleur à valider (ex: "#FF0000" ou "#F00")

        Returns:
            bool: True si la couleur est valide, False sinon
        """
        import re

        pattern = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
        return bool(re.match(pattern, color)) if color else False

    @classmethod
    def create_category(
        cls,
        name: str,
        is_expense: bool,
        user_id: Optional[int] = None,
        description: Optional[str] = None,
        color: str = "#6c757d",
        icon: str = "fa-tag",
        monthly_budget: Optional[Decimal] = None,
        is_default: bool = False,
        category_type: str = "expense",
    ) -> Category:
        """
        Crée une nouvelle catégorie.

        Args:
            name: Nom de la catégorie (obligatoire)
            is_expense: True pour une catégorie de dépense, False pour un revenu
            user_id: ID de l'utilisateur propriétaire (None pour les catégories globales)
            description: Description optionnelle de la catégorie
            color: Couleur au format hexadécimal (ex: #28a745)
            icon: Classe CSS de l'icône (ex: 'fa-utensils')
            monthly_budget: Budget mensuel alloué (optionnel)
            is_default: Si la catégorie est une catégorie système par défaut

        Returns:
            Category: La catégorie créée

        Raises:
            CategoryValidationError: Si les données sont invalides
            CategoryIntegrityError: En cas de violation de contrainte d'intégrité
            CategoryError: Pour toutes les autres erreurs

        Example:
            >>> category = CategoryService.create_category(
            ...     name="Nourriture",
            ...     is_expense=True,
            ...     color="#28a745",
            ...     user_id=1
            ... )
            >>> category.name
            'Nourriture'
        """
        try:
            # Validation des données obligatoires
            if not name or not isinstance(name, str):
                raise CategoryValidationError("Le nom de la catégorie est obligatoire")

            # Validation du format de la couleur
            if not cls._is_valid_hex_color(color):
                raise CategoryValidationError(
                    "La couleur doit être au format hexadécimal (ex: #FF0000)"
                )

            # Validation du type de catégorie (contrainte CHECK en base)
            if category_type not in ("expense", "income", "transfer"):
                raise CategoryValidationError(
                    "Type de catégorie invalide. Doit être 'expense', 'income' ou 'transfer'"
                )

            # Vérification de l'unicité du nom
            query = Category.query.filter(db.func.lower(Category.name) == name.lower())

            if user_id is not None:
                query = query.filter(
                    (Category.user_id == user_id)
                    | (Category.user_id.is_(None) & ~Category.is_default)
                )
            else:
                query = query.filter(Category.user_id.is_(None))

            if query.first() is not None:
                raise CategoryIntegrityError(
                    f"Une catégorie avec le nom '{name}' existe déjà"
                )

            # Création de la catégorie
            category = Category(
                name=name,
                is_expense=is_expense,
                description=description,
                color=color,
                icon=icon,
                monthly_budget=monthly_budget,
                is_default=is_default,
                user_id=user_id if not is_default else None,
                category_type=category_type,
            )

            db.session.add(category)
            db.session.commit()

            # 📧 Notification de création de catégorie
            if user_id:  # Ne notifier que pour les catégories utilisateur
                try:
                    from core.services.notifications import NotificationService

                    category_type = "dépense" if is_expense else "revenu"
                    NotificationService.send_notification(
                        user_id=user_id,
                        title="Nouvelle catégorie créée",
                        message=f"La catégorie '{name}' ({category_type}) a été créée avec succès",
                        notification_type="category_created",
                        action_url="/categories/",
                        send_email=True,
                        metadata={
                            "category_id": category.id,
                            "category_name": name,
                            "category_type": category_type,
                            "color": color,
                        },
                    )
                except Exception as e:
                    db.session.rollback()
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Erreur envoi notification création catégorie: {e}")

            return category

        except IntegrityError as e:
            db.session.rollback()
            if "unique" in str(e).lower():
                raise CategoryIntegrityError(
                    f"Une catégorie avec ce nom existe déjà"
                ) from e
            raise CategoryError(
                f"Erreur lors de la création de la catégorie: {str(e)}"
            ) from e

        except SQLAlchemyError as e:
            db.session.rollback()
            raise CategoryError(
                f"Erreur lors de la création de la catégorie: {str(e)}"
            ) from e

    @classmethod
    def update_category(
        cls,
        category_id: int,
        user_id: int,
        name: Optional[str] = None,
        is_expense: Optional[bool] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        monthly_budget: Optional[Decimal] = None,
        is_default: Optional[bool] = None,
        category_type: Optional[str] = None,
    ) -> Category:
        """
        Met à jour une catégorie existante.

        Args:
            category_id: Identifiant unique de la catégorie à mettre à jour
            user_id: Identifiant de l'utilisateur effectuant la requête
            name: Nouveau nom de la catégorie
            is_expense: True pour une catégorie de dépense, False pour un revenu
            description: Nouvelle description de la catégorie
            color: Nouvelle couleur au format hexadécimal
            icon: Nouvelle icône (classe CSS)
            monthly_budget: Nouveau budget mensuel alloué
            is_default: Si la catégorie est une catégorie système par défaut

        Returns:
            Category: La catégorie mise à jour

        Raises:
            CategoryNotFoundError: Si la catégorie n'existe pas
            CategoryPermissionError: Si l'utilisateur n'a pas les droits
            CategoryValidationError: Si les données sont invalides
            CategoryIntegrityError: En cas de violation de contrainte d'intégrité
            CategoryError: Pour toutes les autres erreurs

        Example:
            >>> category = CategoryService.update_category(
            ...     category_id=1,
            ...     user_id=1,
            ...     name="Restaurant",
            ...     color="#dc3545"
            ... )
            >>> category.name
            'Restaurant'
        """
        try:
            # Récupération de la catégorie avec vérification des permissions
            category = cls.get_category(category_id, user_id, allow_global=False)

            # Sauvegarder les anciennes valeurs pour la notification
            old_name = category.name
            old_type = "dépense" if category.is_expense else "revenu"

            # Vérification si la catégorie peut être modifiée
            if category.is_default:
                raise CategoryPermissionError(
                    "Les catégories par défaut ne peuvent pas être modifiées"
                )

            # Mise à jour des champs avec validation
            if name is not None and name != category.name:
                # Vérification de l'unicité du nom (même règle que la
                # création : les catégories globales par défaut n'entrent
                # pas en conflit avec les catégories personnelles)
                existing = Category.query.filter(
                    db.func.lower(Category.name) == name.lower(),
                    (Category.user_id == user_id)
                    | (Category.user_id.is_(None) & ~Category.is_default),
                    Category.id != category_id,
                ).first()

                if existing:
                    raise CategoryIntegrityError(
                        f"Une catégorie avec le nom '{name}' existe déjà"
                    )
                category.name = name

            if is_expense is not None:
                category.is_expense = is_expense

            if category_type is not None:
                if category_type not in ("expense", "income", "transfer"):
                    raise CategoryValidationError(
                        "Type de catégorie invalide. Doit être 'expense', 'income' ou 'transfer'"
                    )
                category.category_type = category_type

            if description is not None:
                category.description = description

            if color is not None:
                if not cls._is_valid_hex_color(color):
                    raise CategoryValidationError(
                        "La couleur doit être au format hexadécimal (ex: #FF0000)"
                    )
                category.color = color

            if icon is not None:
                category.icon = icon

            if monthly_budget is not None:
                category.monthly_budget = monthly_budget

            if is_default is not None and is_default != category.is_default:
                if is_default:
                    # Si on essaie de rendre la catégorie par défaut, on la rend globale
                    category.user_id = None
                category.is_default = is_default

            # Mise à jour de la date de modification
            category.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            # 📧 Notification de modification de catégorie
            try:
                from core.services.notifications import NotificationService

                changes = []
                if name and name != old_name:
                    changes.append(f"nom: '{old_name}' → '{category.name}'")
                if is_expense is not None:
                    new_type = "dépense" if category.is_expense else "revenu"
                    if new_type != old_type:
                        changes.append(f"type: {old_type} → {new_type}")

                if changes:
                    NotificationService.send_notification(
                        user_id=user_id,
                        title="Catégorie modifiée",
                        message=f"La catégorie '{category.name}' a été modifiée: {', '.join(changes)}",
                        notification_type="category_updated",
                        action_url="/categories/",
                        send_email=True,
                        metadata={
                            "category_id": category.id,
                            "category_name": category.name,
                            "changes": changes,
                        },
                    )
            except Exception as e:
                db.session.rollback()
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Erreur envoi notification modification catégorie: {e}")

            return category

        except IntegrityError as e:
            db.session.rollback()
            if "unique" in str(e).lower():
                raise CategoryIntegrityError(
                    "Une catégorie avec ce nom existe déjà"
                ) from e
            raise CategoryError(
                f"Erreur lors de la mise à jour de la catégorie: {str(e)}"
            ) from e

        except SQLAlchemyError as e:
            db.session.rollback()
            raise CategoryError(
                f"Erreur lors de la mise à jour de la catégorie: {str(e)}"
            ) from e

    @classmethod
    def delete_category(
        cls, category_id: int, user_id: int, force: bool = False
    ) -> bool:
        """
        Supprime une catégorie.

        Args:
            category_id: Identifiant unique de la catégorie à supprimer
            user_id: Identifiant de l'utilisateur effectuant la requête
            force: Si True, force la suppression même si la catégorie est utilisée
                (déconseillé car peut créer des incohérences)

        Returns:
            bool: True si la suppression a réussi, False sinon

        Raises:
            CategoryNotFoundError: Si la catégorie n'existe pas
            CategoryPermissionError: Si l'utilisateur n'a pas les droits
            CategoryIntegrityError: Si la catégorie est utilisée et force=False
            CategoryError: Pour toutes les autres erreurs

        Example:
            >>> CategoryService.delete_category(1, 1)
            True
        """
        try:
            # Récupération de la catégorie avec vérification des permissions
            category = cls.get_category(category_id, user_id, allow_global=False)

            # Sauvegarder les infos pour la notification
            category_name = category.name
            category_type = "dépense" if category.is_expense else "revenu"
            transaction_count = category.transactions.count()

            # Vérification si la catégorie peut être supprimée
            if category.is_default:
                raise CategoryPermissionError(
                    "Les catégories par défaut ne peuvent pas être supprimées"
                )

            # Vérification des contraintes d'intégrité
            if not force and transaction_count > 0:
                raise CategoryIntegrityError(
                    "Impossible de supprimer une catégorie associée à des transactions. "
                    "Utilisez force=True pour forcer la suppression."
                )

            # Si force=True, on réaffecte les transactions à la catégorie par défaut correspondante
            if force and transaction_count > 0:
                default_category = Category.query.filter(
                    Category.is_default == True,
                    Category.is_expense == category.is_expense,
                    Category.user_id.is_(None),
                ).first()

                if default_category:
                    # Mise à jour des transactions
                    from core.models.transactions import Transaction

                    Transaction.query.filter_by(category_id=category.id).update(
                        {"category_id": default_category.id}
                    )
                    db.session.flush()

            # Suppression de la catégorie
            db.session.delete(category)
            db.session.commit()

            # 📧 Notification de suppression de catégorie
            try:
                from core.services.notifications import NotificationService

                message = (
                    f"La catégorie '{category_name}' ({category_type}) a été supprimée"
                )
                if transaction_count > 0 and force:
                    message += f" avec {transaction_count} transaction(s) réaffectée(s)"

                NotificationService.send_notification(
                    user_id=user_id,
                    title="Catégorie supprimée",
                    message=message,
                    notification_type="category_deleted",
                    action_url="/categories/",
                    send_email=True,
                    metadata={
                        "category_name": category_name,
                        "category_type": category_type,
                        "transaction_count": transaction_count,
                        "forced_deletion": force,
                    },
                )
            except Exception as e:
                db.session.rollback()
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Erreur envoi notification suppression catégorie: {e}")

            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            raise CategoryError(
                f"Erreur lors de la suppression de la catégorie: {str(e)}"
            ) from e

    @classmethod
    def get_default_categories(
        cls, category_type: Optional[str] = None
    ) -> List[Category]:
        """
        Récupère les catégories par défaut du système, éventuellement filtrées par type.

        Args:
            category_type: Type de catégories à récupérer ('expense', 'income', 'transfer')
                Si None, retourne toutes les catégories par défaut.

        Returns:
            List[Category]: Liste des catégories par défaut correspondant au filtre

        Raises:
            CategoryValidationError: Si le type de catégorie est invalide
            CategoryError: Pour toutes les autres erreurs

        Example:
            >>> # Récupérer toutes les catégories par défaut
            >>> categories = CategoryService.get_default_categories()

            >>> # Récupérer uniquement les catégories de dépenses par défaut
            >>> expense_cats = CategoryService.get_default_categories('expense')
        """
        try:
            # Validation du type de catégorie si spécifié
            if category_type and category_type not in [
                "expense",
                "income",
                "transfer",
            ]:
                raise CategoryValidationError(
                    "Type de catégorie invalide. Doit être 'expense', 'income' ou 'transfer'"
                )

            query = Category.query.filter_by(is_default=True, user_id=None)

            # Filtrage par type si spécifié
            if category_type:
                query = query.filter_by(category_type=category_type)

            return query.order_by(Category.name).all()

        except SQLAlchemyError as e:
            raise CategoryError(
                f"Erreur lors de la récupération des catégories par défaut: {str(e)}"
            ) from e

    @classmethod
    def ensure_default_categories_exist(cls) -> None:
        """
        Vérifie et crée les catégories par défaut si elles n'existent pas.

        Cette méthode est généralement appelée au démarrage de l'application.

        Raises:
            CategoryError: En cas d'erreur lors de la création des catégories
        """
        try:
            # Catégories de dépenses par défaut
            expense_categories = [
                {
                    "name": "Alimentation",
                    "category_type": "expense",
                    "icon": "shopping-cart",
                    "color": "#28a745",
                },
                {
                    "name": "Logement",
                    "category_type": "expense",
                    "icon": "home",
                    "color": "#007bff",
                },
                {
                    "name": "Transport",
                    "category_type": "expense",
                    "icon": "car",
                    "color": "#6f42c1",
                },
                {
                    "name": "Loisirs",
                    "category_type": "expense",
                    "icon": "film",
                    "color": "#ffc107",
                },
                {
                    "name": "Santé",
                    "category_type": "expense",
                    "icon": "heart",
                    "color": "#e83e8c",
                },
                {
                    "name": "Éducation",
                    "category_type": "expense",
                    "icon": "book",
                    "color": "#20c997",
                },
                {
                    "name": "Autres dépenses",
                    "category_type": "expense",
                    "icon": "shopping-bag",
                    "color": "#6c757d",
                },
            ]

            # Catégories de revenus par défaut
            income_categories = [
                {
                    "name": "Salaire",
                    "category_type": "income",
                    "icon": "credit-card",
                    "color": "#28a745",
                },
                {
                    "name": "Prime",
                    "category_type": "income",
                    "icon": "gift",
                    "color": "#17a2b8",
                },
                {
                    "name": "Investissements",
                    "category_type": "income",
                    "icon": "chart-line",
                    "color": "#6f42c1",
                },
                {
                    "name": "Vente",
                    "category_type": "income",
                    "icon": "tag",
                    "color": "#fd7e14",
                },
                {
                    "name": "Autres revenus",
                    "category_type": "income",
                    "icon": "wallet",
                    "color": "#20c997",
                },
            ]

            # Catégories de transferts par défaut
            transfer_categories = [
                {
                    "name": "Virement entre comptes",
                    "category_type": "transfer",
                    "icon": "exchange-alt",
                    "color": "#6c757d",
                },
                {
                    "name": "Retrait",
                    "category_type": "transfer",
                    "icon": "money-bill-wave",
                    "color": "#17a2b8",
                },
                {
                    "name": "Dépôt",
                    "category_type": "transfer",
                    "icon": "hand-holding-usd",
                    "color": "#28a745",
                },
            ]

            all_defaults = expense_categories + income_categories + transfer_categories
            existing_defaults = {cat.name: cat for cat in cls.get_default_categories()}

            # Création des catégories manquantes
            for cat_data in all_defaults:
                if cat_data["name"] not in existing_defaults:
                    category = Category(
                        name=cat_data["name"],
                        category_type=cat_data["category_type"],
                        is_expense=cat_data["category_type"] != "income",
                        description="Catégorie par défaut",
                        icon=cat_data["icon"],
                        color=cat_data["color"],
                        is_default=True,
                        user_id=None,
                    )
                    db.session.add(category)

            db.session.commit()

        except SQLAlchemyError as e:
            db.session.rollback()
            raise CategoryError(
                f"Erreur lors de la création des catégories par défaut: {str(e)}"
            ) from e

    @classmethod
    def ensure_user_has_default_categories(cls, user_id: int) -> None:
        """
        S'assure qu'un utilisateur dispose de toutes les catégories par défaut.

        Crée des copies personnelles des catégories par défaut pour l'utilisateur
        si elles n'existent pas déjà.

        Args:
            user_id: Identifiant de l'utilisateur

        Raises:
            CategoryError: En cas d'erreur lors de la création des catégories
        """
        try:
            default_categories = cls.get_default_categories()

            for default_cat in default_categories:
                # Vérifier si l'utilisateur a déjà une catégorie avec ce nom
                existing = Category.query.filter(
                    db.func.lower(Category.name) == default_cat.name.lower(),
                    Category.user_id == user_id,
                ).first()

                if not existing:
                    # Créer une copie personnelle pour l'utilisateur
                    user_category = Category(
                        name=default_cat.name,
                        category_type=default_cat.category_type,
                        is_expense=default_cat.is_expense,
                        description=default_cat.description or "Catégorie par défaut",
                        icon=default_cat.icon,
                        color=default_cat.color,
                        is_default=False,
                        user_id=user_id,
                    )
                    db.session.add(user_category)

            db.session.commit()

        except SQLAlchemyError as e:
            db.session.rollback()
            raise CategoryError(
                f"Erreur lors de la création des catégories par défaut pour l'utilisateur: {str(e)}"
            ) from e
