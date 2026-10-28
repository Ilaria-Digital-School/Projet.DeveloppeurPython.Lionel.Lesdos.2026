"""
API REST v1 — Rapports.

Routes:
    GET    /api/v1/rapports              Liste des rapports sauvegardés
    POST   /api/v1/rapports/generate     Générer un rapport
    GET    /api/v1/rapports/data         Données de rapport pour graphiques
    GET    /api/v1/rapports/<id>         Récupérer un rapport sauvegardé
    DELETE /api/v1/rapports/<id>         Supprimer un rapport sauvegardé
    GET    /api/v1/rapports/export       Exporter un rapport (pdf, excel, csv, json)
    GET    /api/v1/rapports/export/pdf   Exporter un rapport en PDF (alias)
"""

import csv
import json
import logging
from datetime import datetime, timedelta
from io import BytesIO, StringIO

from flask import make_response, request
from flask_login import current_user, login_required
from sqlalchemy import func

from core.extensions import db
from core.models.category import Category
from core.models.report import Report
from core.models.transactions import Transaction, TransactionType

from . import api_v1_bp
from .auth import auth_limiter
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


# =============================
# FONCTIONS UTILITAIRES PRIVEES
# =============================


def _resolve_date_range(date_range, params):
    """Résout une période en dates de début et fin."""
    today = datetime.now().date()

    if date_range == "current_month":
        start_date = today.replace(day=1)
        end_date = today
    elif date_range == "last_month":
        first_of_month = today.replace(day=1)
        end_date = first_of_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif date_range == "last_6_months":
        start_date = (today - timedelta(days=180)).replace(day=1)
        end_date = today
    elif date_range == "current_year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif date_range == "last_year":
        start_date = today.replace(year=today.year - 1, month=1, day=1)
        end_date = today.replace(year=today.year - 1, month=12, day=31)
    elif date_range == "custom":
        start_str = params.get("start_date")
        end_str = params.get("end_date")
        start_date = (
            datetime.strptime(start_str, "%Y-%m-%d").date()
            if start_str
            else today.replace(day=1)
        )
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else today
    else:
        start_date = today.replace(day=1)
        end_date = today

    return start_date, end_date


def _normalize_report_type(report_type):
    """Normalise le type de rapport (accepte underscore et tiret)."""
    return report_type.replace("_", "-") if report_type else "expenses"


def _generate_expenses_report(user_id, start_date, end_date):
    """Génère un rapport de dépenses par catégorie."""
    # Jointure externe : les dépenses sans catégorie sont comptées sous
    # "Non catégorisée" (sinon le total diverge du rapport revenus/dépenses)
    results = (
        db.session.query(
            func.coalesce(Category.name, "Non catégorisée").label("category"),
            func.sum(Transaction.montant).label("total"),
        )
        .select_from(Transaction)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user_id,
            func.date(Transaction.date_heure_transaction) >= start_date,
            func.date(Transaction.date_heure_transaction) <= end_date,
            Transaction.type_transaction.in_(TransactionType.expense_values()),
        )
        .group_by(Category.name)
        .order_by(func.sum(Transaction.montant).desc())
        .all()
    )

    categories = []
    amounts = []
    total = 0.0
    for row in results:
        amount = abs(float(row.total or 0))
        categories.append(row.category)
        amounts.append(amount)
        total += amount

    # Calculer les pourcentages
    data_items = []
    for cat, amt in zip(categories, amounts):
        pct = round((amt / total * 100), 1) if total > 0 else 0
        data_items.append({"category": cat, "amount": amt, "percentage": pct})

    return {
        "categories": categories,
        "amounts": amounts,
        "total": total,
        "items": data_items,
    }


def _generate_income_vs_expenses_report(user_id, start_date, end_date):
    """Génère un rapport revenus vs dépenses par mois."""
    expense_types = TransactionType.expense_values()
    income_types = TransactionType.income_values()

    # Dépenses par mois
    expenses = (
        db.session.query(
            func.date_trunc("month", Transaction.date_heure_transaction).label(
                "period"
            ),
            func.sum(Transaction.montant).label("total"),
        )
        .filter(
            Transaction.user_id == user_id,
            func.date(Transaction.date_heure_transaction) >= start_date,
            func.date(Transaction.date_heure_transaction) <= end_date,
            Transaction.type_transaction.in_(expense_types),
        )
        .group_by("period")
        .order_by("period")
        .all()
    )

    # Revenus par mois
    incomes = (
        db.session.query(
            func.date_trunc("month", Transaction.date_heure_transaction).label(
                "period"
            ),
            func.sum(Transaction.montant).label("total"),
        )
        .filter(
            Transaction.user_id == user_id,
            func.date(Transaction.date_heure_transaction) >= start_date,
            func.date(Transaction.date_heure_transaction) <= end_date,
            Transaction.type_transaction.in_(income_types),
        )
        .group_by("period")
        .order_by("period")
        .all()
    )

    expense_map = {str(r.period)[:7]: abs(float(r.total or 0)) for r in expenses}
    income_map = {str(r.period)[:7]: float(r.total or 0) for r in incomes}

    all_periods = sorted(set(list(expense_map.keys()) + list(income_map.keys())))

    periods = []
    expenses_data = []
    income_data = []
    for p in all_periods:
        periods.append(p)
        expenses_data.append(expense_map.get(p, 0))
        income_data.append(income_map.get(p, 0))

    total_income = sum(income_data)
    total_expenses = sum(expenses_data)

    return {
        "periods": periods,
        "expenses": expenses_data,
        "income": income_data,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "savings": total_income - total_expenses,
    }


def _generate_cashflow_report(user_id, start_date, end_date):
    """Génère un rapport de flux de trésorerie."""
    income_data = _generate_income_vs_expenses_report(user_id, start_date, end_date)

    # Calculer le flux net cumulé
    cumulative = []
    running_total = 0
    for inc, exp in zip(income_data["income"], income_data["expenses"]):
        running_total += inc - exp
        cumulative.append(running_total)

    income_data["cumulative"] = cumulative
    return income_data


def _build_pdf_report(
    report_type, report_data, start_date, end_date, include_charts=False
):
    """Construit un document PDF pour un rapport."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )

    styles = getSampleStyleSheet()
    elements = []

    # Titre
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
        alignment=1,
        textColor=colors.darkblue,
    )

    type_labels = {
        "expenses": "Rapport des Depenses par Categorie",
        "expenses_by_category": "Rapport des Depenses par Categorie",
        "expenses-by-category": "Rapport des Depenses par Categorie",
        "income-vs-expenses": "Rapport Revenus vs Depenses",
        "cashflow": "Rapport Flux de Tresorerie",
    }
    title_text = type_labels.get(report_type, "Rapport Financier")
    elements.append(Paragraph(title_text, title_style))
    elements.append(Spacer(1, 10))

    # Sous-titre avec période
    period_text = f"Periode : du {start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}"
    elements.append(Paragraph(period_text, styles["Normal"]))
    elements.append(
        Paragraph(
            f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}", styles["Normal"]
        )
    )
    elements.append(Spacer(1, 20))

    if report_type in ("expenses", "expenses_by_category", "expenses-by-category"):
        _add_expenses_pdf_content(elements, styles, report_data)
        if include_charts:
            _add_expenses_chart(elements, report_data)
    elif report_type in ("income-vs-expenses", "cashflow"):
        _add_income_vs_expenses_pdf_content(elements, styles, report_data)
        if include_charts:
            _add_income_vs_expenses_chart(elements, report_data)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def _add_expenses_pdf_content(elements, styles, data):
    """Ajoute le contenu d'un rapport de dépenses au PDF."""
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    total = data.get("total", 0)
    elements.append(
        Paragraph(f"Total des depenses : {total:.2f} EUR", styles["Heading2"])
    )
    elements.append(Spacer(1, 15))

    items = data.get("items", [])
    if items:
        table_data = [["Categorie", "Montant", "%"]]
        for item in items:
            table_data.append(
                [
                    item["category"],
                    f"{item['amount']:.2f} EUR",
                    f"{item['percentage']}%",
                ]
            )
        table_data.append(["TOTAL", f"{total:.2f} EUR", "100%"])

        table = Table(table_data, colWidths=[250, 120, 80])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.beige, colors.white]),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.lightblue),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(table)
    else:
        elements.append(
            Paragraph("Aucune depense trouvee pour cette periode.", styles["Normal"])
        )


def _add_income_vs_expenses_pdf_content(elements, styles, data):
    """Ajoute le contenu d'un rapport revenus/dépenses au PDF."""
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    total_income = data.get("total_income", 0)
    total_expenses = data.get("total_expenses", 0)
    savings = data.get("savings", 0)

    summary_style = styles["Heading2"]
    elements.append(
        Paragraph(f"Revenus totaux : {total_income:.2f} EUR", summary_style)
    )
    elements.append(
        Paragraph(f"Depenses totales : {total_expenses:.2f} EUR", summary_style)
    )
    elements.append(Paragraph(f"Economies : {savings:.2f} EUR", summary_style))
    elements.append(Spacer(1, 15))

    periods = data.get("periods", [])
    incomes = data.get("income", [])
    expenses_list = data.get("expenses", [])

    if periods:
        table_data = [["Periode", "Revenus", "Depenses", "Solde"]]
        for p, inc, exp in zip(periods, incomes, expenses_list):
            balance = inc - exp
            table_data.append(
                [p, f"{inc:.2f} EUR", f"{exp:.2f} EUR", f"{balance:.2f} EUR"]
            )
        table_data.append(
            [
                "TOTAL",
                f"{total_income:.2f} EUR",
                f"{total_expenses:.2f} EUR",
                f"{savings:.2f} EUR",
            ]
        )

        table = Table(table_data, colWidths=[100, 120, 120, 120])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.beige, colors.white]),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.lightblue),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(table)
    else:
        elements.append(
            Paragraph("Aucune donnee trouvee pour cette periode.", styles["Normal"])
        )


def _add_expenses_chart(elements, data):
    """Génère un camembert matplotlib des dépenses par catégorie et l'ajoute au PDF."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from reportlab.platypus import Image, Spacer

    items = data.get("items", [])
    if not items:
        return

    categories = [item["category"] for item in items]
    amounts = [item["amount"] for item in items]

    fig, ax = plt.subplots(1, 1, figsize=(6, 4))
    colors = plt.cm.Set3(range(len(categories)))
    wedges, texts, autotexts = ax.pie(
        amounts,
        labels=categories,
        autopct="%1.1f%%",
        colors=colors,
        textprops={"fontsize": 8},
    )
    ax.set_title("Repartition des depenses par categorie", fontsize=10)
    plt.tight_layout()

    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    img_buffer.seek(0)

    elements.append(Spacer(1, 20))
    img = Image(img_buffer, width=400, height=270)
    elements.append(img)


def _add_income_vs_expenses_chart(elements, data):
    """Génère un graphique barres revenus/dépenses par période et l'ajoute au PDF."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from reportlab.platypus import Image, Spacer

    periods = data.get("periods", [])
    incomes = data.get("income", [])
    expenses = data.get("expenses", [])

    if not periods:
        return

    fig, ax = plt.subplots(1, 1, figsize=(7, 4))
    x = range(len(periods))
    width = 0.35

    ax.bar([i - width / 2 for i in x], incomes, width, label="Revenus", color="#10B981")
    ax.bar(
        [i + width / 2 for i in x], expenses, width, label="Depenses", color="#EF4444"
    )

    ax.set_xlabel("Periode")
    ax.set_ylabel("Montant (EUR)")
    ax.set_title("Revenus vs Depenses par mois", fontsize=10)
    ax.set_xticks(list(x))
    ax.set_xticklabels(periods, rotation=45, ha="right", fontsize=8)
    ax.legend()
    plt.tight_layout()

    img_buffer = BytesIO()
    fig.savefig(img_buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    img_buffer.seek(0)

    elements.append(Spacer(1, 20))
    img = Image(img_buffer, width=430, height=250)
    elements.append(img)


def _build_excel_report(report_type, data, start_date, end_date):
    """Construit un fichier Excel (.xlsx) pour un rapport."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="4472C4", end_color="4472C4", fill_type="solid"
    )

    type_labels = {
        "expenses": "Depenses par Categorie",
        "expenses_by_category": "Depenses par Categorie",
        "expenses-by-category": "Depenses par Categorie",
        "income-vs-expenses": "Revenus vs Depenses",
        "cashflow": "Flux de Tresorerie",
    }
    ws.title = type_labels.get(report_type, "Rapport")[:31]

    # En-tête du rapport
    ws.append([f'Rapport: {type_labels.get(report_type, "Financier")}'])
    ws.append(
        [
            f'Periode: du {start_date.strftime("%d/%m/%Y")} au {end_date.strftime("%d/%m/%Y")}'
        ]
    )
    ws.append([f'Genere le {datetime.now().strftime("%d/%m/%Y a %H:%M")}'])
    ws.append([])

    if report_type in ("expenses", "expenses_by_category", "expenses-by-category"):
        headers = ["Categorie", "Montant (EUR)", "Pourcentage (%)"]
        ws.append(headers)
        row_idx = ws.max_row
        for col_idx, _ in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        items = data.get("items", [])
        for item in items:
            ws.append([item["category"], item["amount"], item["percentage"]])

        ws.append([])
        ws.append(["TOTAL", data.get("total", 0), "100%"])

        # Auto-ajuster les colonnes
        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 15
        ws.column_dimensions["C"].width = 15

    elif report_type in ("income-vs-expenses", "cashflow"):
        headers = ["Periode", "Revenus (EUR)", "Depenses (EUR)", "Solde (EUR)"]
        ws.append(headers)
        row_idx = ws.max_row
        for col_idx, _ in enumerate(headers, 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        periods = data.get("periods", [])
        incomes = data.get("income", [])
        expenses = data.get("expenses", [])
        for p, inc, exp in zip(periods, incomes, expenses):
            ws.append([p, inc, exp, inc - exp])

        ws.append([])
        ws.append(
            [
                "TOTAL",
                data.get("total_income", 0),
                data.get("total_expenses", 0),
                data.get("savings", 0),
            ]
        )

        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 15
        ws.column_dimensions["C"].width = 15
        ws.column_dimensions["D"].width = 15

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def _build_csv_report(report_type, data):
    """Construit un fichier CSV pour un rapport."""
    output = StringIO()
    writer = csv.writer(output)

    if report_type in ("expenses", "expenses_by_category", "expenses-by-category"):
        writer.writerow(["Categorie", "Montant (EUR)", "Pourcentage (%)"])
        items = data.get("items", [])
        for item in items:
            writer.writerow([item["category"], item["amount"], item["percentage"]])
        writer.writerow(["TOTAL", data.get("total", 0), "100"])

    elif report_type in ("income-vs-expenses", "cashflow"):
        writer.writerow(["Periode", "Revenus (EUR)", "Depenses (EUR)", "Solde (EUR)"])
        periods = data.get("periods", [])
        incomes = data.get("income", [])
        expenses = data.get("expenses", [])
        for p, inc, exp in zip(periods, incomes, expenses):
            writer.writerow([p, inc, exp, inc - exp])
        writer.writerow(
            [
                "TOTAL",
                data.get("total_income", 0),
                data.get("total_expenses", 0),
                data.get("savings", 0),
            ]
        )

    return output.getvalue()


def _build_json_report(report_type, data, start_date, end_date):
    """Construit un export JSON structuré pour un rapport."""
    type_labels = {
        "expenses": "Depenses par Categorie",
        "expenses_by_category": "Depenses par Categorie",
        "expenses-by-category": "Depenses par Categorie",
        "income-vs-expenses": "Revenus vs Depenses",
        "cashflow": "Flux de Tresorerie",
    }

    export = {
        "report": {
            "type": report_type,
            "title": type_labels.get(report_type, "Rapport Financier"),
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "generated_at": datetime.now().isoformat(),
        },
        "data": data,
    }

    return json.dumps(export, ensure_ascii=False, indent=2, default=str)


# =============================
# ROUTES API
# =============================

# -- LIST -------------------------------------------------------------------


@api_v1_bp.route("/rapports", methods=["GET"])
@login_required
def api_reports_list():
    """Liste des rapports sauvegardés."""
    try:
        user_id = current_user.id
        from core.services.reports.report_services import ReportService

        reports = ReportService.get_user_reports(user_id)

        reports_data = [
            {
                "id": r.id,
                "name": r.name,
                "type": r.report_type,
                "parameters": r.parameters,
                "is_public": r.is_public,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in reports
        ]

        return api_success(reports_data)

    except Exception as e:
        logger.error(f"Erreur liste rapports: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# -- GENERATE ---------------------------------------------------------------


@api_v1_bp.route("/rapports/generate", methods=["POST"])
@login_required
@auth_limiter.limit("10 per minute")
def api_reports_generate():
    """Génère un rapport avec les filtres spécifiés."""
    try:
        user_id = current_user.id
        data = request.get_json()
        if not data:
            return api_error("Données manquantes", 400)

        report_type = _normalize_report_type(data.get("report_type", "expenses"))
        date_range = data.get("date_range", "current_month")
        name = data.get("name")

        # Calculer les dates selon la période
        start_date, end_date = _resolve_date_range(date_range, data)

        # Générer selon le type
        if report_type in ("expenses", "expenses-by-category"):
            report_data = _generate_expenses_report(user_id, start_date, end_date)
        elif report_type == "income-vs-expenses":
            report_data = _generate_income_vs_expenses_report(
                user_id, start_date, end_date
            )
        elif report_type == "cashflow":
            report_data = _generate_cashflow_report(user_id, start_date, end_date)
        else:
            report_data = _generate_expenses_report(user_id, start_date, end_date)

        # Sauvegarder si un nom est fourni
        saved_report = None
        if name:
            from core.services.reports.report_services import ReportService

            saved_report = ReportService.save_report(
                user_id=user_id,
                name=name,
                report_type=report_type,
                parameters={
                    "date_range": date_range,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )

        return api_success(
            {
                "id": saved_report.id if saved_report else None,
                "report_type": report_type,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "data": report_data,
            }
        )

    except Exception as e:
        logger.error(f"Erreur génération rapport: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# -- DATA (charts) ----------------------------------------------------------


@api_v1_bp.route("/rapports/data", methods=["GET"])
@login_required
def api_reports_data():
    """Données de rapport pour les graphiques frontend."""
    try:
        user_id = current_user.id
        date_range = request.args.get("date_range", "current_month")
        report_type = _normalize_report_type(
            request.args.get("report_type", "expenses")
        )

        start_date, end_date = _resolve_date_range(date_range, request.args)

        if report_type in ("expenses", "expenses-by-category"):
            data = _generate_expenses_report(user_id, start_date, end_date)
        elif report_type == "income-vs-expenses":
            data = _generate_income_vs_expenses_report(user_id, start_date, end_date)
        elif report_type == "cashflow":
            data = _generate_cashflow_report(user_id, start_date, end_date)
        else:
            data = _generate_expenses_report(user_id, start_date, end_date)

        return api_success(
            {
                "report_type": report_type,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "data": data,
            }
        )

    except Exception as e:
        logger.error(f"Erreur données rapport: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# -- GET by ID --------------------------------------------------------------


@api_v1_bp.route("/rapports/<int:report_id>", methods=["GET"])
@login_required
def api_reports_get(report_id):
    """Récupère un rapport sauvegardé."""
    try:
        report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()
        if not report:
            return api_error("Rapport non trouvé", 404)

        # Régénérer les données à partir des paramètres sauvegardés
        params = report.parameters or {}
        start_str = params.get("start_date")
        end_str = params.get("end_date")
        start_date = (
            datetime.fromisoformat(start_str).date()
            if start_str
            else datetime.now().date().replace(day=1)
        )
        end_date = (
            datetime.fromisoformat(end_str).date() if end_str else datetime.now().date()
        )

        normalized_type = _normalize_report_type(report.report_type)
        if normalized_type in ("expenses", "expenses-by-category"):
            data = _generate_expenses_report(current_user.id, start_date, end_date)
        elif normalized_type == "income-vs-expenses":
            data = _generate_income_vs_expenses_report(
                current_user.id, start_date, end_date
            )
        elif normalized_type == "cashflow":
            data = _generate_cashflow_report(current_user.id, start_date, end_date)
        else:
            data = _generate_expenses_report(current_user.id, start_date, end_date)

        return api_success(
            {
                "id": report.id,
                "name": report.name,
                "type": report.report_type,
                "parameters": report.parameters,
                "created_at": report.created_at.isoformat(),
                "data": data,
            }
        )

    except Exception as e:
        logger.error(f"Erreur récupération rapport {report_id}: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# -- DELETE -----------------------------------------------------------------


@api_v1_bp.route("/rapports/<int:report_id>", methods=["DELETE"])
@login_required
def api_reports_delete(report_id):
    """Supprime un rapport sauvegardé."""
    try:
        report = Report.query.filter_by(id=report_id, user_id=current_user.id).first()
        if not report:
            return api_error("Rapport non trouvé", 404)

        db.session.delete(report)
        db.session.commit()

        return api_success(message="Rapport supprimé")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur suppression rapport {report_id}: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


# -- EXPORT MULTI-FORMAT ----------------------------------------------------


@api_v1_bp.route("/rapports/export", methods=["GET"])
@login_required
@auth_limiter.limit("10 per minute")
def api_reports_export():
    """Exporte un rapport au format spécifié (pdf, excel, csv, json)."""
    try:
        user_id = current_user.id
        export_format = request.args.get("format", "pdf").lower()
        include_charts = request.args.get("include_charts", "false").lower() == "true"
        date_range = request.args.get("date_range", "current_month")
        report_type = _normalize_report_type(
            request.args.get("report_type", "expenses")
        )

        start_date, end_date = _resolve_date_range(date_range, request.args)

        # Générer les données du rapport
        if report_type in ("expenses", "expenses-by-category"):
            report_data = _generate_expenses_report(user_id, start_date, end_date)
        elif report_type == "income-vs-expenses":
            report_data = _generate_income_vs_expenses_report(
                user_id, start_date, end_date
            )
        elif report_type == "cashflow":
            report_data = _generate_cashflow_report(user_id, start_date, end_date)
        else:
            report_data = _generate_expenses_report(user_id, start_date, end_date)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if export_format == "pdf":
            pdf_buffer = _build_pdf_report(
                report_type,
                report_data,
                start_date,
                end_date,
                include_charts=include_charts,
            )
            response = make_response(pdf_buffer.getvalue())
            response.headers["Content-Type"] = "application/pdf"
            response.headers["Content-Disposition"] = (
                f"attachment; filename=rapport_{report_type}_{timestamp}.pdf"
            )

        elif export_format == "excel":
            excel_buffer = _build_excel_report(
                report_type, report_data, start_date, end_date
            )
            response = make_response(excel_buffer.getvalue())
            response.headers["Content-Type"] = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response.headers["Content-Disposition"] = (
                f"attachment; filename=rapport_{report_type}_{timestamp}.xlsx"
            )

        elif export_format == "csv":
            csv_content = _build_csv_report(report_type, report_data)
            response = make_response(csv_content)
            response.headers["Content-Type"] = "text/csv; charset=utf-8"
            response.headers["Content-Disposition"] = (
                f"attachment; filename=rapport_{report_type}_{timestamp}.csv"
            )

        elif export_format == "json":
            json_content = _build_json_report(
                report_type, report_data, start_date, end_date
            )
            response = make_response(json_content)
            response.headers["Content-Type"] = "application/json; charset=utf-8"
            response.headers["Content-Disposition"] = (
                f"attachment; filename=rapport_{report_type}_{timestamp}.json"
            )

        else:
            return api_error(
                f"Format d'export non supporté: {export_format}. Formats valides: pdf, excel, csv, json",
                400,
            )

        logger.info(
            f"Export {export_format} rapport '{report_type}' pour user {user_id}"
        )
        return response

    except ImportError as e:
        logger.error(f"Module manquant pour l'export: {e}")
        return api_error(f"Export non disponible. Module manquant: {e}", 500)
    except Exception as e:
        logger.error(
            f"Erreur export {request.args.get('format', 'pdf')}: {e}", exc_info=True
        )
        return api_error("Une erreur interne est survenue", 500)


# -- EXPORT PDF (alias pour compatibilité) ----------------------------------


@api_v1_bp.route("/rapports/export/pdf", methods=["GET"])
@login_required
@auth_limiter.limit("10 per minute")
def api_reports_export_pdf():
    """Exporte un rapport au format PDF (alias de /export?format=pdf)."""
    try:
        user_id = current_user.id
        include_charts = request.args.get("include_charts", "false").lower() == "true"
        date_range = request.args.get("date_range", "current_month")
        report_type = _normalize_report_type(
            request.args.get("report_type", "expenses")
        )

        start_date, end_date = _resolve_date_range(date_range, request.args)

        # Générer les données du rapport
        if report_type in ("expenses", "expenses-by-category"):
            report_data = _generate_expenses_report(user_id, start_date, end_date)
        elif report_type == "income-vs-expenses":
            report_data = _generate_income_vs_expenses_report(
                user_id, start_date, end_date
            )
        elif report_type == "cashflow":
            report_data = _generate_cashflow_report(user_id, start_date, end_date)
        else:
            report_data = _generate_expenses_report(user_id, start_date, end_date)

        # Générer le PDF
        pdf_buffer = _build_pdf_report(
            report_type,
            report_data,
            start_date,
            end_date,
            include_charts=include_charts,
        )

        response = make_response(pdf_buffer.getvalue())
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = (
            f'attachment; filename=rapport_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )

        logger.info(f"Export PDF rapport '{report_type}' pour user {user_id}")
        return response

    except ImportError:
        logger.error("Module reportlab non disponible")
        return api_error("Export PDF non disponible. Module reportlab manquant.", 500)
    except Exception as e:
        logger.error(f"Erreur export PDF: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
