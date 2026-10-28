"""
Modèle pour l'historique des modifications de budget.
"""

from datetime import datetime, timezone

from core.extensions import db


class BudgetHistory(db.Model):
    """Historique des modifications d'un budget"""

    __tablename__ = "budget_history"

    id = db.Column(db.Integer, primary_key=True)
    # Nullable + SET NULL : l'historique (dont l'entrée "delete") survit à la
    # suppression du budget ; NOT NULL faisait échouer toute suppression d'un
    # budget ayant un historique
    budget_id = db.Column(
        db.Integer,
        db.ForeignKey("budgets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = db.Column(db.String(20), nullable=False)  # create, update, delete
    changes = db.Column(db.JSON)  # Stocke les changements au format JSON
    changed_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    ip_address = db.Column(db.String(45))  # IPv6 peut faire jusqu'à 45 caractères

    # Relations
    # Utilisation de références simples pour éviter les conflits d'importation
    budget = db.relationship(
        "Budget", backref=db.backref("history", lazy="dynamic", passive_deletes=True)
    )
    user = db.relationship("User", backref="budget_history")

    def __repr__(self):
        return f"<BudgetHistory {self.id} - {self.action} - {self.changed_at}>"
