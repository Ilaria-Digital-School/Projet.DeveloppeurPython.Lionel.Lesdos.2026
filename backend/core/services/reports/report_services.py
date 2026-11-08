"""
Services pour la génération et la gestion des rapports.

Ce module contient la logique métier pour la génération de rapports,
la manipulation des données et l'exportation dans différents formats.
"""

import matplotlib

matplotlib.use("Agg")  # Utiliser un backend non interactif
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import or_

from core.models import db

# Import direct du modèle Report (évite conflit SQLAlchemy)
from core.models.report import Report

# Configuration des styles pour les graphiques
sns.set_theme(style="whitegrid")
plt.style.use("seaborn-v0_8")


class ReportService:
    """Service pour la génération et la gestion des rapports."""

    @staticmethod
    def save_report(
        user_id: int,
        name: str,
        report_type: str,
        parameters: Dict[str, Any],
        is_public: bool = False,
    ) -> Report:
        """
        Enregistre un rapport personnalisé.

        Args:
            user_id: ID de l'utilisateur
            name: Nom du rapport
            report_type: Type de rapport
            parameters: Paramètres du rapport
            is_public: Si le rapport est public

        Returns:
            Instance du rapport enregistré
        """
        report = Report(
            user_id=user_id,
            name=name,
            report_type=report_type,
            parameters=parameters,
            is_public=is_public,
        )

        db.session.add(report)
        db.session.commit()

        return report

    @staticmethod
    def get_user_reports(user_id: int, include_public: bool = False) -> List[Report]:
        """
        Récupère les rapports d'un utilisateur.

        Args:
            user_id: ID de l'utilisateur
            include_public: Inclure les rapports publics d'autres utilisateurs

        Returns:
            Liste des rapports
        """
        query = Report.query

        if include_public:
            query = query.filter(
                or_(Report.user_id == user_id, Report.is_public == True)
            )
        else:
            query = query.filter_by(user_id=user_id)

        return query.order_by(Report.updated_at.desc()).all()
