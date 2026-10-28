"""
Modèle pour les rapports personnalisés
"""

from datetime import datetime, timezone

from core.extensions import db


class Report(db.Model):
    """Modèle pour les rapports personnalisés"""

    __tablename__ = "reports"
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
    name = db.Column(db.String(100), nullable=False)
    report_type = db.Column(
        db.String(50), nullable=False
    )  # 'expenses', 'income', 'category', etc.
    parameters = db.Column(
        db.JSON, nullable=False
    )  # Paramètres du rapport (filtres, etc.)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
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
    user = db.relationship("User", back_populates="reports")
    # Relation vers ReportData définie après la classe


# ReportData class temporairement supprimée pour résoudre conflit SQLAlchemy
# Les données de rapport peuvent être stockées directement dans Report.data (JSON)
