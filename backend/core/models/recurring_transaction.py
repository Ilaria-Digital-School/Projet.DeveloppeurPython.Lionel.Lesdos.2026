"""
Modèle pour les transactions récurrentes.

Permet de définir des templates de transactions qui seront
automatiquement créées selon une fréquence définie.
"""

from datetime import datetime, timezone

from core.extensions import db


class RecurringTransaction(db.Model):
    """Modèle pour les transactions récurrentes"""

    __tablename__ = "recurring_transactions"
    # Requête du scheduler : is_active AND next_execution_date <= aujourd'hui
    __table_args__ = (
        db.Index("ix_recurring_tx_active_next", "is_active", "next_execution_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Références de compte
    account_id = db.Column(
        db.Integer, db.ForeignKey("ComptesBancaires.id_compte"), nullable=False
    )
    destination_account_id = db.Column(
        db.Integer, db.ForeignKey("ComptesBancaires.id_compte"), nullable=True
    )
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    # Template de la transaction
    montant = db.Column(db.Numeric(10, 2), nullable=False)
    type_transaction = db.Column(db.String(50), nullable=False)
    libelle = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    devise = db.Column(db.String(3), default="EUR")

    # Paramètres de récurrence
    frequency = db.Column(
        db.String(20), nullable=False
    )  # daily, weekly, monthly, yearly
    interval = db.Column(
        db.Integer, default=1, nullable=False
    )  # tous les N jours/semaines/mois/ans
    day_of_month = db.Column(db.Integer, nullable=True)  # 1-31 pour monthly
    day_of_week = db.Column(
        db.Integer, nullable=True
    )  # 0=lundi, 6=dimanche pour weekly

    # Dates de contrôle
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    next_execution_date = db.Column(db.Date, nullable=False)
    last_executed_date = db.Column(db.Date, nullable=True)

    # État
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    # Échecs d'exécution consécutifs (remis à 0 au premier succès) et raison du
    # dernier : au bout de MAX_ECHECS, le scheduler met la récurrence en pause
    echecs_consecutifs = db.Column(
        db.Integer, default=0, server_default="0", nullable=False
    )
    derniere_erreur = db.Column(db.String(255), nullable=True)

    # Audit
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relations
    user = db.relationship(
        "User", backref=db.backref("recurring_transactions", lazy="dynamic")
    )
    account = db.relationship("Account", foreign_keys=[account_id])
    destination_account = db.relationship(
        "Account", foreign_keys=[destination_account_id]
    )
    category = db.relationship("Category")

    def to_dict(self):
        return {
            "id": self.id,
            "account_id": self.account_id,
            "account_name": self.account.name if self.account else None,
            "destination_account_id": self.destination_account_id,
            "destination_account_name": (
                self.destination_account.name if self.destination_account else None
            ),
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "montant": float(self.montant),
            "type_transaction": self.type_transaction,
            "libelle": self.libelle,
            "notes": self.notes,
            "devise": self.devise,
            "frequency": self.frequency,
            "interval": self.interval,
            "day_of_month": self.day_of_month,
            "day_of_week": self.day_of_week,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "next_execution_date": (
                self.next_execution_date.isoformat()
                if self.next_execution_date
                else None
            ),
            "last_executed_date": (
                self.last_executed_date.isoformat() if self.last_executed_date else None
            ),
            "is_active": self.is_active,
            "echecs_consecutifs": self.echecs_consecutifs or 0,
            "derniere_erreur": self.derniere_erreur,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "frequency_display": self._frequency_display(),
        }

    def to_api_dict(self):
        """Convertit la transaction récurrente en dictionnaire avec clés anglaises pour l'API."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "account_name": self.account.name if self.account else None,
            "destination_account_id": self.destination_account_id,
            "destination_account_name": (
                self.destination_account.name if self.destination_account else None
            ),
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "amount": float(self.montant),
            "transaction_type": self.type_transaction,
            "description": self.libelle,
            "notes": self.notes,
            "currency": self.devise,
            "frequency": self.frequency,
            "interval": self.interval,
            "day_of_month": self.day_of_month,
            "day_of_week": self.day_of_week,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "next_execution_date": (
                self.next_execution_date.isoformat()
                if self.next_execution_date
                else None
            ),
            "last_executed_date": (
                self.last_executed_date.isoformat() if self.last_executed_date else None
            ),
            "is_active": self.is_active,
            "echecs_consecutifs": self.echecs_consecutifs or 0,
            "derniere_erreur": self.derniere_erreur,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "frequency_display": self._frequency_display(),
        }

    def _frequency_display(self):
        """Retourne un libellé lisible de la fréquence"""
        labels = {
            "daily": "Quotidien",
            "weekly": "Hebdomadaire",
            "monthly": "Mensuel",
            "yearly": "Annuel",
        }
        base = labels.get(self.frequency, self.frequency)
        if self.interval and self.interval > 1:
            units = {
                "daily": "jours",
                "weekly": "semaines",
                "monthly": "mois",
                "yearly": "ans",
            }
            return f"Tous les {self.interval} {units.get(self.frequency, '')}"
        return base
