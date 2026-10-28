"""
Modèle pour la gestion des budgets
"""

import calendar
from datetime import date, datetime, timezone

from sqlalchemy import func

from core.extensions import db


class Budget(db.Model):
    """Modèle pour les budgets"""

    __tablename__ = "budgets"
    __table_args__ = {
        "extend_existing": True
    }  # Permet de redéfinir la table si elle existe déjà

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    spent_amount = db.Column(db.Numeric(10, 2), default=0.00)
    period = db.Column(db.String(20), nullable=False)  # monthly, yearly, custom
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    notification_sent = db.Column(db.Boolean, default=False)
    notification_threshold = db.Column(db.Integer, default=90)  # Pourcentage
    # Dernière alerte envoyée : "<début de période ISO>:<niveau>" (niveau =
    # seuil du budget ou 100) ; évite les doublons et repart à chaque période
    derniere_alerte = db.Column(db.String(32), nullable=True)

    # Relations SQLAlchemy avec des références simples
    # Utilisation de strings pour les relations pour éviter les imports circulaires
    category = db.relationship("Category", back_populates="budgets")
    user = db.relationship("User", back_populates="budgets")

    def periode_courante(self, today=None):
        """Période de dépense en cours : (début, fin), ou None si le budget
        n'est pas actif à cette date.

        monthly : le mois civil en cours ; yearly : l'année civile en cours ;
        autre (custom) : start_date -> end_date. Toujours limitée aux dates
        du budget.
        """
        today = today or date.today()
        if today < self.start_date or (self.end_date and today > self.end_date):
            return None
        if self.period == "yearly":
            debut, fin = date(today.year, 1, 1), date(today.year, 12, 31)
        elif self.period == "monthly":
            debut = today.replace(day=1)
            fin = debut.replace(day=calendar.monthrange(debut.year, debut.month)[1])
        else:
            debut, fin = self.start_date, self.end_date or today
        debut = max(debut, self.start_date)
        if self.end_date:
            fin = min(fin, self.end_date)
        return debut, fin

    def get_used_amount(self, today=None):
        """Montant dépensé sur la période en cours (cf. periode_courante)."""
        from core.models.transactions import Transaction, TransactionType

        if not self.id:
            return 0.0
        periode = self.periode_courante(today)
        if periode is None:
            return 0.0
        debut, fin = periode

        # Comparaison sur la date (pas la date-heure) : sinon "<= fin" excluait
        # les dépenses du dernier jour passé minuit
        query = db.session.query(
            func.coalesce(func.sum(Transaction.montant), 0)
        ).filter(
            Transaction.user_id == self.user_id,
            Transaction.type_transaction.in_(TransactionType.expense_values()),
            func.date(Transaction.date_heure_transaction) >= debut,
            func.date(Transaction.date_heure_transaction) <= fin,
        )
        if self.category_id:
            query = query.filter(Transaction.category_id == self.category_id)
        return float(query.scalar() or 0.0)

    def to_dict(self):
        """Convertit le budget en dictionnaire avec clés anglaises."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "amount": float(self.amount) if self.amount is not None else None,
            "spent_amount": (
                float(self.spent_amount) if self.spent_amount is not None else 0.0
            ),
            "period": self.period,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "notification_sent": self.notification_sent,
            "notification_threshold": self.notification_threshold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Budget {self.id} - {self.amount}>"
