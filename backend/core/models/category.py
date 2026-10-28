from datetime import datetime, timezone

# Import de l'instance db depuis le module core.extensions
from core.extensions import db

# Transaction sera référencé par string pour éviter l'import circulaire


class Category(db.Model):
    """Modèle représentant une catégorie de transactions.

    Attributes:
        id (int): Identifiant unique de la catégorie
        user_id (int): Référence à l'utilisateur propriétaire (NULL pour les catégories globales)
        name (str): Nom de la catégorie
        description (str): Description détaillée
        color (str): Code couleur hexadécimal
        icon (str): Classe CSS de l'icône
        is_expense (bool): Si la catégorie est pour les dépenses
        monthly_budget (Decimal): Budget mensuel alloué (optionnel)
        created_at (DateTime): Date de création
        updated_at (DateTime): Dernière mise à jour
    """

    __tablename__ = "categories"
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_category_user_name"),
        db.CheckConstraint(
            "category_type IN ('expense', 'income', 'transfer')",
            name="ck_categories_category_type",
        ),
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)

    # Clé étrangère vers l'utilisateur (NULL pour les catégories globales)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        info={"description": "Référence à l'utilisateur propriétaire"},
    )

    # Informations de base
    name = db.Column(
        "name",
        db.String(100),
        nullable=False,
        index=True,
        info={"description": "Nom de la catégorie"},
    )
    description = db.Column(
        "description",
        db.Text,
        nullable=True,
        info={"description": "Description détaillée de la catégorie"},
    )

    # Métadonnées d'affichage
    color = db.Column(
        "color",
        db.String(7),
        default="#6c757d",
        info={"description": "Couleur au format hexadécimal (#RRGGBB)"},
    )
    icon = db.Column(
        "icon",
        db.String(50),
        default="fa-tag",
        info={"description": "Classe CSS de l'icône (ex: fa-tag)"},
    )

    # Type de catégorie (dépense ou revenu)
    is_expense = db.Column(
        "is_expense",
        db.Boolean,
        default=True,
        nullable=False,
        index=True,
        info={"description": "Si la catégorie est pour les dépenses"},
    )

    # Type explicite de catégorie (income, expense, transfer)
    category_type = db.Column(
        "category_type",
        db.String(20),
        default="expense",
        nullable=False,
        info={"description": "Type explicite: income, expense, transfer"},
    )

    # Budget mensuel (optionnel)
    monthly_budget = db.Column(
        "monthly_budget",
        db.Numeric(10, 2),
        nullable=True,
        info={"description": "Budget mensuel alloué à cette catégorie"},
    )

    # Métadonnées
    created_at = db.Column(
        "created_at",
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        info={"description": "Date de création"},
    )
    updated_at = db.Column(
        "updated_at",
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        info={"description": "Dernière mise à jour"},
    )

    # Indique si c'est une catégorie par défaut (globale)
    is_default = db.Column(
        "is_default",
        db.Boolean,
        default=False,
        nullable=False,
        server_default=db.text("FALSE"),
        info={"description": "Si la catégorie est une catégorie système par défaut"},
    )

    # Relation avec les transactions (côté many)
    transactions = db.relationship(
        "Transaction",  # Utilisation du nom simple pour éviter les imports circulaires
        back_populates="category",
        lazy="dynamic",
        cascade="all, delete-orphan",
        info={"description": "Transactions associées à cette catégorie"},
    )

    # Relation avec les budgets (utilise le nom de la classe en chaîne pour éviter les imports circulaires)
    budgets = db.relationship(
        "Budget",
        back_populates="category",
        lazy="dynamic",
        cascade="all, delete-orphan",
        info={"description": "Budgets associés à cette catégorie"},
    )

    def __repr__(self):
        return f"<Category {self.name} (ID: {self.id})>"

    @property
    def is_global(self):
        """Vérifie si la catégorie est globale (sans propriétaire)."""
        return self.user_id is None

    @classmethod
    def get_default_categories(cls, is_expense=True):
        """Récupère les catégories par défaut pour un type donné."""
        return cls.query.filter_by(is_default=True, is_expense=is_expense).all()

    def to_dict(self):
        """Convertit la catégorie en dictionnaire pour la sérialisation JSON."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "is_expense": self.is_expense,
            "monthly_budget": (
                float(self.monthly_budget) if self.monthly_budget else None
            ),
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
