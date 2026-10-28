"""
Services pour la génération et la gestion des rapports.

Ce module contient la logique métier pour la génération de rapports,
la manipulation des données et l'exportation dans différents formats.
"""

from datetime import datetime, timezone
from io import BytesIO

import matplotlib
import pandas as pd

matplotlib.use("Agg")  # Utiliser un backend non interactif
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import func, or_

from core.models import Category, db

# Import direct du modèle Report (évite conflit SQLAlchemy)
from core.models.report import Report
from core.models.transactions import Transaction, TransactionType

# Configuration des styles pour les graphiques
sns.set_theme(style="whitegrid")
plt.style.use("seaborn-v0_8")


class ReportService:
    """Service pour la génération et la gestion des rapports."""

    @staticmethod
    def generate_expense_report(
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "category",
        include_subcategories: bool = True,
    ) -> Dict[str, Any]:
        """
        Génère un rapport de dépenses par catégorie.

        Args:
            user_id: ID de l'utilisateur
            start_date: Date de début de la période
            end_date: Date de fin de la période
            group_by: Champ de groupement ('category', 'date', 'payment_method')
            include_subcategories: Inclure les sous-catégories

        Returns:
            Dict contenant les données du rapport

        Raises:
            ValueError: Si les paramètres sont invalides
        """
        if not user_id or not start_date or not end_date:
            raise ValueError("Tous les paramètres sont obligatoires")

        if start_date > end_date:
            raise ValueError("La date de début doit être antérieure à la date de fin")

        # Construction de la requête de base
        query = (
            db.session.query(
                Category.name.label("category_name"),
                func.sum(Transaction.montant).label("total_amount"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.type_transaction.in_(TransactionType.expense_values()),
                Transaction.date_heure_transaction.between(start_date, end_date),
            )
        )

        # Gestion des sous-catégories
        if not include_subcategories:
            query = query.filter(Category.parent_id.isnot(None))

        # Groupement des résultats
        if group_by == "category":
            query = query.group_by(Category.name)
        elif group_by == "date":
            query = query.group_by(Transaction.date_heure_transaction)
        elif group_by == "payment_method":
            query = query.group_by(Transaction.type_transaction)

        # Exécution de la requête
        results = query.order_by(func.sum(Transaction.montant).desc()).all()

        # Formatage des résultats
        categories = [r.category_name for r in results]
        amounts = [float(r.total_amount) for r in results]

        return {
            "report_type": "expense",
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "data": {
                "categories": categories,
                "amounts": amounts,
                "total": sum(amounts) if amounts else 0,
            },
            "metadata": {
                "group_by": group_by,
                "include_subcategories": include_subcategories,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    @staticmethod
    def generate_income_vs_expenses_report(
        user_id: int, start_date: datetime, end_date: datetime, group_by: str = "month"
    ) -> Dict[str, Any]:
        """
        Génère un rapport comparant les revenus et les dépenses.

        Args:
            user_id: ID de l'utilisateur
            start_date: Date de début de la période
            end_date: Date de fin de la période
            group_by: Période de groupement ('day', 'week', 'month', 'year')

        Returns:
            Dict contenant les données du rapport
        """
        # Validation des paramètres
        if not user_id or not start_date or not end_date:
            raise ValueError("Tous les paramètres sont obligatoires")

        if start_date > end_date:
            raise ValueError("La date de début doit être antérieure à la date de fin")

        # Déterminer la colonne de groupement en fonction de la période
        if group_by == "day":
            date_column = func.date(Transaction.date_heure_transaction)
        elif group_by == "week":
            date_column = func.date_trunc("week", Transaction.date_heure_transaction)
        elif group_by == "month":
            date_column = func.date_trunc("month", Transaction.date_heure_transaction)
        elif group_by == "year":
            date_column = func.date_trunc("year", Transaction.date_heure_transaction)
        else:
            raise ValueError(f"Valeur de group_by non valide: {group_by}")

        # Requête pour les dépenses
        expenses_query = (
            db.session.query(
                date_column.label("period"),
                func.sum(Transaction.montant).label("total"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.type_transaction.in_(TransactionType.expense_values()),
                Transaction.date_heure_transaction.between(start_date, end_date),
            )
            .group_by("period")
        )

        # Requête pour les revenus
        income_query = (
            db.session.query(
                date_column.label("period"),
                func.sum(Transaction.montant).label("total"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.type_transaction.in_(TransactionType.income_values()),
                Transaction.date_heure_transaction.between(start_date, end_date),
            )
            .group_by("period")
        )

        # Exécution des requêtes
        expenses = {str(r.period): float(r.total) for r in expenses_query.all()}
        income = {str(r.period): float(r.total) for r in income_query.all()}

        # Toutes les périodes uniques
        all_periods = sorted(set(list(expenses.keys()) + list(income.keys())))

        # Préparation des données pour le graphique
        periods = []
        expenses_data = []
        income_data = []

        for period in all_periods:
            periods.append(period)
            expenses_data.append(expenses.get(period, 0))
            income_data.append(income.get(period, 0))

        return {
            "report_type": "income_vs_expenses",
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "data": {
                "periods": periods,
                "expenses": expenses_data,
                "income": income_data,
            },
            "metadata": {
                "group_by": group_by,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    @staticmethod
    def export_report(
        report_data: Dict[str, Any],
        export_format: str = "pdf",
        include_charts: bool = True,
        include_data: bool = True,
        resolution: str = "medium",
    ) -> BytesIO:
        """
        Exporte un rapport dans le format spécifié.

        Args:
            report_data: Données du rapport à exporter
            export_format: Format d'export ('pdf', 'csv', 'excel', 'json')
            include_charts: Inclure les graphiques dans l'export
            include_data: Inclure les données brutes dans l'export
            resolution: Résolution des graphiques ('low', 'medium', 'high')

        Returns:
            BytesIO contenant le fichier exporté

        Raises:
            ValueError: Si le format d'export n'est pas pris en charge
        """
        if export_format not in ["pdf", "csv", "excel", "json"]:
            raise ValueError(f"Format d'export non pris en charge: {export_format}")

        output = BytesIO()

        if export_format == "pdf":
            # Implémentation de l'export PDF
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            # Création du document PDF
            doc = SimpleDocTemplate(output, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            # Titre du rapport
            title_style = ParagraphStyle(
                "Title",
                parent=styles["Heading1"],
                fontSize=18,
                spaceAfter=20,
                alignment=1,  # Centré
            )

            title = f"Rapport: {report_data.get('report_type', 'Sans titre')}"
            elements.append(Paragraph(title, title_style))

            # Période du rapport
            period = report_data.get("period", {})
            period_text = (
                f"Période: {period.get('start', 'N/A')} au {period.get('end', 'N/A')}"
            )
            elements.append(Paragraph(period_text, styles["Normal"]))
            elements.append(Spacer(1, 20))

            # Ajout des graphiques si demandé
            if include_charts and report_data["report_type"] == "expense":
                # Création d'un graphique camembert
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.pie(
                    report_data["data"]["amounts"],
                    labels=report_data["data"]["categories"],
                    autopct="%1.1f%%",
                    startangle=90,
                )
                ax.axis("equal")  # Assure que le graphique est un cercle

                # Sauvegarde du graphique dans un buffer
                chart_buffer = BytesIO()
                plt.savefig(chart_buffer, format="png", dpi=300, bbox_inches="tight")
                plt.close()

                # Ajout de l'image au PDF
                from reportlab.platypus import Image

                chart_buffer.seek(0)
                elements.append(Image(chart_buffer, width=400, height=300))
                elements.append(Spacer(1, 20))

            # Ajout des données brutes si demandé
            if include_data:
                data = report_data.get("data", {})
                if "categories" in data and "amounts" in data:
                    # Création d'un tableau avec les données
                    table_data = [["Catégorie", "Montant"]]
                    for cat, amount in zip(data["categories"], data["amounts"]):
                        table_data.append([cat, f"{amount:.2f} €"])

                    # Création du tableau
                    table = Table(table_data)
                    table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, 0), 10),
                                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ]
                        )
                    )

                    elements.append(table)

            # Génération du PDF
            doc.build(elements)

        elif export_format == "csv":
            # Export CSV
            import csv

            data = report_data.get("data", {})
            if "categories" in data and "amounts" in data:
                writer = csv.writer(output)
                writer.writerow(["Catégorie", "Montant"])
                for cat, amount in zip(data["categories"], data["amounts"]):
                    writer.writerow([cat, f"{amount:.2f}"])

        elif export_format == "excel":
            # Export Excel
            data = report_data.get("data", {})
            if "categories" in data and "amounts" in data:
                df = pd.DataFrame(
                    {"Catégorie": data["categories"], "Montant": data["amounts"]}
                )
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df.to_excel(writer, sheet_name="Rapport", index=False)

        elif export_format == "json":
            # Export JSON
            import json

            json.dump(report_data, output, indent=2, ensure_ascii=False)

        output.seek(0)
        return output

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

    @staticmethod
    def generate_chart(
        data: Dict[str, Any],
        title: str,
        x_label: str,
        y_label: str,
        chart_type: str = "bar",
        x_field: str = None,
        y_field: str = None,
    ) -> BytesIO:
        """
        Génère un graphique à partir des données fournies.

        Args:
            data: Données à afficher
            title: Titre du graphique
            x_label: Libellé de l'axe X
            y_label: Libellé de l'axe Y
            chart_type: Type de graphique ('bar', 'line', 'pie')
            x_field: Champ à utiliser pour l'axe X
            y_field: Champ à utiliser pour l'axe Y

        Returns:
            BytesIO contenant l'image du graphique
        """
        try:
            plt.figure(figsize=(12, 6))

            if chart_type == "bar":
                if x_field and y_field:
                    x = [str(item.get(x_field)) for item in data]
                    y = [item.get(y_field, 0) for item in data]
                    sns.barplot(x=x, y=y)
                else:
                    # Si pas de champs spécifiés, utiliser les clés/valeurs du premier niveau
                    x = list(data.keys())
                    y = list(data.values())
                    sns.barplot(x=x, y=y)

            elif chart_type == "line":
                if x_field and y_field:
                    x = [item.get(x_field) for item in data]
                    y = [item.get(y_field, 0) for item in data]
                    sns.lineplot(x=x, y=y, marker="o")
                else:
                    # Trier par clés pour les données temporelles
                    sorted_data = sorted(data.items())
                    x = [str(k) for k, v in sorted_data]
                    y = [v for k, v in sorted_data]
                    sns.lineplot(x=x, y=y, marker="o")

            elif chart_type == "pie":
                if x_field and y_field:
                    labels = [str(item.get(x_field)) for item in data]
                    sizes = [item.get(y_field, 0) for item in data]
                else:
                    # Utiliser les clés/valeurs du premier niveau
                    labels = [str(k) for k in data.keys()]
                    sizes = list(data.values())

                plt.pie(sizes, labels=labels, autopct="%1.1f%%")
                plt.axis("equal")  # Assure que le graphique est un cercle

            else:
                raise ValueError(f"Type de graphique non pris en charge: {chart_type}")

            # Configuration des étiquettes et du titre
            if chart_type != "pie":
                plt.xlabel(x_label)
                plt.ylabel(y_label)
                plt.xticks(rotation=45, ha="right")

            plt.title(title)
            plt.tight_layout()

            # Sauvegarde du graphique dans un buffer
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
            plt.close()
            img_buffer.seek(0)

            return img_buffer

        except Exception as e:
            # En cas d'erreur, retourner un graphique d'erreur
            plt.figure(figsize=(8, 4))
            plt.text(
                0.5,
                0.5,
                f"Erreur: {str(e)}",
                horizontalalignment="center",
                verticalalignment="center",
                transform=plt.gca().transAxes,
            )
            plt.axis("off")

            img_buffer = BytesIO()
            plt.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
            plt.close()
            img_buffer.seek(0)

            return img_buffer
