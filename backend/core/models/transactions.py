"""
Modèle de données pour les transactions financières.

Ce module contient les classes Transaction et TransactionType qui représentent
les opérations financières dans l'application.
"""

from datetime import datetime, timezone
from enum import Enum

# Import de l'instance db depuis le module core.extensions
from core.extensions import db

# Import direct du modèle Account pour éviter les conflits SQLAlchemy
from core.models.account import Account


class TransactionType(str, Enum):
    """
    Énumération des types de transactions financières.
    """

    # Types de revenus (entrées d'argent)
    SALAIRE = "salaire"  # Salaire
    REVENU_AUTRE = "revenu_autre"  # Autre type de revenu
    REMBOURSEMENT = "remboursement"  # Remboursement

    # Types de dépenses (sorties d'argent)
    ACHAT = "achat"  # Achat de biens
    EXPENSE = "expense"  # Dépense générique (compatibilité)
    LOYER = "loyer"  # Loyer
    FACTURE = "facture"  # Factures (électricité, eau, etc.)
    ABONNEMENT = "abonnement"  # Abonnements divers

    # Transferts
    VIREMENT = "virement"  # Virement entre comptes
    PRELEVEMENT = "prelevement"  # Prélèvement automatique

    @classmethod
    def get_choices(cls):
        """Retourne une liste de tuples (valeur, libellé) pour les formulaires."""
        display_names = {
            "salaire": "Salaire",
            "revenu_autre": "Autre revenu",
            "remboursement": "Remboursement",
            "achat": "Achat",
            "expense": "Dépense",
            "loyer": "Loyer",
            "facture": "Facture",
            "abonnement": "Abonnement",
            "virement": "Virement",
            "prelevement": "Prélèvement automatique",
        }
        return [
            (member.value, display_names.get(member.value, member.value))
            for member in cls
        ]

    @classmethod
    def get_display_name(cls, value):
        """Retourne le nom d'affichage pour une valeur donnée."""
        display_names = {
            "salaire": "Salaire",
            "revenu_autre": "Autre revenu",
            "remboursement": "Remboursement",
            "achat": "Achat",
            "expense": "Dépense",
            "loyer": "Loyer",
            "facture": "Facture",
            "abonnement": "Abonnement",
            "virement": "Virement",
            "prelevement": "Prélèvement automatique",
        }
        if value is None:
            return ""
        return display_names.get(value, value) if isinstance(value, str) else str(value)

    @property
    def display_name(self):
        """Retourne le nom d'affichage du type de transaction."""
        display_names = {
            "salaire": "Salaire",
            "revenu_autre": "Autre revenu",
            "remboursement": "Remboursement",
            "achat": "Achat",
            "expense": "Dépense",
            "loyer": "Loyer",
            "facture": "Facture",
            "abonnement": "Abonnement",
            "virement": "Virement",
            "prelevement": "Prélèvement automatique",
        }
        return display_names.get(self.value, self.value)

    @property
    def is_income(self):
        """Détermine si le type de transaction représente une entrée d'argent."""
        return self in [
            TransactionType.SALAIRE,
            TransactionType.REVENU_AUTRE,
            TransactionType.REMBOURSEMENT,
        ]

    @property
    def is_expense(self):
        """Détermine si le type de transaction représente une sortie d'argent."""
        return self in [
            TransactionType.ACHAT,
            TransactionType.EXPENSE,
            TransactionType.LOYER,
            TransactionType.FACTURE,
            TransactionType.ABONNEMENT,
            TransactionType.PRELEVEMENT,
        ]

    @property
    def is_transfer(self):
        """Détermine si le type de transaction est un virement."""
        return self == TransactionType.VIREMENT

    @classmethod
    def income_values(cls):
        """Retourne les valeurs string des types de revenus (pour filtres SQL)."""
        return [m.value for m in cls if m.is_income] + ["income", "SALAIRE"]

    @classmethod
    def expense_values(cls):
        """Retourne les valeurs string des types de depenses (pour filtres SQL)."""
        return [m.value for m in cls if m.is_expense] + ["ACHAT"]

    @classmethod
    def transfer_values(cls):
        """Retourne les valeurs string des types de virements (le frontend envoie 'virement')."""
        return [m.value for m in cls if m.is_transfer] + ["transfer"]


class Transaction(db.Model):
    """
    Modèle représentant une transaction financière.
    """

    __tablename__ = "transactions"

    # Définition explicite de la table pour éviter les problèmes de redéfinition
    __table__ = db.Table(
        "transactions",
        db.metadata,
        db.Column(
            "id",
            db.Integer,
            primary_key=True,
            autoincrement=True,
            nullable=False,
            doc="Identifiant unique de la transaction",
        ),
        db.Column(
            "user_id",
            db.Integer,
            db.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            doc="Identifiant de l'utilisateur propriétaire de la transaction",
        ),
        db.Column(
            "account_id",
            db.Integer,
            db.ForeignKey("ComptesBancaires.id_compte", ondelete="CASCADE"),
            nullable=False,
            index=True,
            doc="Identifiant du compte source (émetteur)",
        ),
        db.Column(
            "destination_account_id",
            db.Integer,
            db.ForeignKey("ComptesBancaires.id_compte", ondelete="SET NULL"),
            nullable=True,
            index=True,
            doc="Identifiant du compte destination (pour les virements)",
        ),
        db.Column(
            "category_id",
            db.Integer,
            db.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            doc="Identifiant de la catégorie de la transaction",
        ),
        db.Column(
            "montant",
            db.Numeric(10, 2),
            nullable=False,
            doc="Montant de la transaction",
        ),
        db.Column(
            "type_transaction",
            db.String(50),
            nullable=False,
            doc="Type de transaction (revenu, dépense, virement, etc.)",
        ),
        db.Column(
            "libelle", db.String(200), nullable=False, doc="Libellé de la transaction"
        ),
        db.Column(
            "notes",
            db.Text,
            nullable=True,
            doc="Notes supplémentaires sur la transaction",
        ),
        db.Column(
            "date_heure_transaction",
            db.DateTime,
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
            doc="Date et heure de la transaction",
        ),
        db.Column(
            "date_valeur",
            db.Date,
            nullable=True,
            doc="Date de valeur de la transaction",
        ),
        db.Column(
            "frais_transaction",
            db.Numeric(12, 2),
            default=0,
            nullable=False,
            doc="Frais associés à la transaction",
        ),
        db.Column(
            "devise",
            db.String(3),
            default="EUR",
            nullable=False,
            doc="Devise de la transaction",
        ),
        db.Column(
            "notes_internes",
            db.Text,
            nullable=True,
            doc="Notes internes non visibles par l'utilisateur",
        ),
        db.Column(
            "statut",
            db.String(50),
            default="comptabilise",
            nullable=False,
            doc="Statut de la transaction",
        ),
        db.Column(
            "date_creation",
            db.DateTime,
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
            doc="Date de création de l'enregistrement",
        ),
        db.Column(
            "date_mise_a_jour",
            db.DateTime,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False,
            doc="Date de dernière mise à jour",
        ),
        db.Index("idx_transaction_date", "date_heure_transaction"),
        db.Index("idx_transaction_type", "type_transaction"),
        db.Index("idx_transaction_account", "account_id"),
        db.Index("idx_transaction_user", "user_id"),
        extend_existing=True,
    )

    # Mappage des colonnes pour l'accès aux attributs
    id = __table__.c.id
    user_id = __table__.c.user_id
    account_id = __table__.c.account_id
    destination_account_id = __table__.c.destination_account_id
    category_id = __table__.c.category_id
    montant = __table__.c.montant
    type_transaction = __table__.c.type_transaction
    libelle = __table__.c.libelle
    notes = __table__.c.notes
    date_heure_transaction = __table__.c.date_heure_transaction
    date_valeur = __table__.c.date_valeur
    frais_transaction = __table__.c.frais_transaction
    devise = __table__.c.devise
    notes_internes = __table__.c.notes_internes
    statut = __table__.c.statut
    date_creation = __table__.c.date_creation
    date_mise_a_jour = __table__.c.date_mise_a_jour

    # Index
    __table_args__ = (
        db.Index("idx_transaction_user", "user_id"),
        db.Index("idx_transaction_account", "account_id"),
        db.Index("idx_transaction_date", "date_heure_transaction"),
        db.Index("idx_transaction_type", "type_transaction"),
    )

    # Relations
    user = db.relationship("User", backref=db.backref("transactions", lazy=True))
    account = db.relationship(
        Account,
        foreign_keys=[account_id],
        primaryjoin="Transaction.account_id == Account.id",
        backref=db.backref("outgoing_transactions", lazy=True),
    )
    destination_account = db.relationship(
        Account,
        foreign_keys=[destination_account_id],
        primaryjoin="Transaction.destination_account_id == Account.id",
        backref=db.backref("incoming_transactions", lazy=True),
    )
    category = db.relationship(
        "Category",
        foreign_keys=[category_id],
        primaryjoin="Transaction.category_id == Category.id",
        back_populates="transactions",
        lazy="joined",
    )

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, type={self.type_transaction}, "
            f"montant={self.montant}, date={self.date_heure_transaction})>"
        )

    def to_dict(self):
        """Convertit la transaction en dictionnaire pour la sérialisation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "destination_account_id": self.destination_account_id,
            "category_id": self.category_id,
            "montant": float(self.montant) if self.montant is not None else None,
            "type_transaction": self.type_transaction,
            "libelle": self.libelle,
            "notes": self.notes,
            "date_heure_transaction": (
                self.date_heure_transaction.isoformat()
                if self.date_heure_transaction
                else None
            ),
            "date_valeur": self.date_valeur.isoformat() if self.date_valeur else None,
            "frais_transaction": (
                float(self.frais_transaction)
                if self.frais_transaction is not None
                else 0.0
            ),
            "devise": self.devise,
            "statut": self.statut,
            "date_creation": (
                self.date_creation.isoformat() if self.date_creation else None
            ),
            "date_mise_a_jour": (
                self.date_mise_a_jour.isoformat() if self.date_mise_a_jour else None
            ),
        }

    def to_api_dict(self):
        """Convertit la transaction en dictionnaire avec clés anglaises pour l'API."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "destination_account_id": self.destination_account_id,
            "category_id": self.category_id,
            "amount": float(self.montant) if self.montant is not None else None,
            "transaction_type": self.type_transaction,
            "description": self.libelle,
            "notes": self.notes,
            "transaction_date": (
                self.date_heure_transaction.isoformat()
                if self.date_heure_transaction
                else None
            ),
            "value_date": self.date_valeur.isoformat() if self.date_valeur else None,
            "fees": (
                float(self.frais_transaction)
                if self.frais_transaction is not None
                else 0.0
            ),
            "currency": self.devise,
            "internal_notes": self.notes_internes,
            "status": self.statut,
            "created_at": (
                self.date_creation.isoformat() if self.date_creation else None
            ),
            "updated_at": (
                self.date_mise_a_jour.isoformat() if self.date_mise_a_jour else None
            ),
        }

    @classmethod
    def from_dict(cls, data):
        """Crée une nouvelle transaction à partir d'un dictionnaire."""
        return cls(
            user_id=data.get("user_id"),
            account_id=data.get("account_id"),
            destination_account_id=data.get("destination_account_id"),
            category_id=data.get("category_id"),
            montant=data.get("montant"),
            type_transaction=data.get("type_transaction"),
            libelle=data.get("libelle"),
            notes=data.get("notes"),
            date_heure_transaction=(
                datetime.fromisoformat(data["date_heure_transaction"])
                if data.get("date_heure_transaction")
                else None
            ),
            date_valeur=(
                datetime.fromisoformat(data["date_valeur"]).date()
                if data.get("date_valeur")
                else None
            ),
            frais_transaction=data.get("frais_transaction", 0.0),
            devise=data.get("devise", "EUR"),
            statut=data.get("statut", "terminee"),
        )

    def update_from_dict(self, data):
        """Met à jour la transaction à partir d'un dictionnaire."""
        for key, value in data.items():
            if hasattr(self, key) and key != "id":
                setattr(self, key, value)
        return self
