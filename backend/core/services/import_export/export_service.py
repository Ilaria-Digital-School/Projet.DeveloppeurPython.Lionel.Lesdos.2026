"""
Service d'export de transactions en CSV, Excel et PDF.

Usage:
    from core.services.import_export.export_service import ExportService

    csv_data = ExportService.to_csv(transactions)          # -> str
    xlsx_data = ExportService.to_excel(transactions)       # -> bytes
    pdf_data = ExportService.to_pdf(transactions)          # -> bytes
"""

import csv
import io
from datetime import datetime


class ExportService:
    """Génère des exports de transactions dans différents formats."""

    HEADERS = [
        "Date",
        "Description",
        "Montant",
        "Type",
        "Compte",
        "Catégorie",
        "Notes",
        "Statut",
        "Frais",
        "Compte destination",
    ]

    @staticmethod
    def _transaction_row(t, full=True):
        """Transforme une transaction en liste de valeurs pour export."""
        row = [
            (
                t.date_heure_transaction.strftime("%d/%m/%Y %H:%M")
                if t.date_heure_transaction
                else ""
            ),
            t.libelle or "",
            f"{t.montant:.2f}".replace(".", ","),
            t.type_transaction or "",
            t.account.name if t.account else "",
            t.category.name if t.category else "",
        ]
        if full:
            row.extend(
                [
                    t.notes_internes or "",
                    t.statut or "",
                    (
                        f"{t.frais_transaction:.2f}".replace(".", ",")
                        if t.frais_transaction
                        else "0,00"
                    ),
                    t.destination_account.name if t.destination_account else "",
                ]
            )
        return row

    @classmethod
    def to_csv(cls, transactions):
        """Exporte les transactions en CSV (str).

        Returns:
            tuple: (csv_string, filename, content_type)
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writerow(cls.HEADERS)
        for t in transactions:
            writer.writerow(cls._transaction_row(t))
        output.seek(0)
        filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return output.getvalue(), filename, "text/csv; charset=utf-8"

    @classmethod
    def to_excel(cls, transactions):
        """Exporte les transactions en Excel (bytes).

        Returns:
            tuple: (bytes_data, filename, content_type)

        Raises:
            ImportError: Si openpyxl n'est pas installé.
        """
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font

        wb = Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(cls.HEADERS)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")
        for t in transactions:
            ws.append(
                [
                    (
                        t.date_heure_transaction.strftime("%d/%m/%Y %H:%M")
                        if t.date_heure_transaction
                        else ""
                    ),
                    t.libelle or "",
                    float(t.montant),
                    t.type_transaction or "",
                    t.account.name if t.account else "",
                    t.category.name if t.category else "",
                    t.notes_internes or "",
                    t.statut or "",
                    float(t.frais_transaction) if t.frais_transaction else 0.0,
                    t.destination_account.name if t.destination_account else "",
                ]
            )
        buf = io.BytesIO()
        wb.save(buf)
        filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return (
            buf.getvalue(),
            filename,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @classmethod
    def to_pdf(cls, transactions):
        """Exporte les transactions en PDF (bytes).

        Returns:
            tuple: (bytes_data, filename, content_type)

        Raises:
            ImportError: Si reportlab n'est pas installé.
        """
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=20,
            alignment=1,
            textColor=colors.darkblue,
        )
        elements.append(
            Paragraph(
                f"Export des Transactions - {datetime.now().strftime('%d/%m/%Y')}",
                title_style,
            )
        )
        elements.append(Spacer(1, 20))

        total = sum(float(t.montant) for t in transactions) if transactions else 0
        elements.append(
            Paragraph(
                f"Nombre: {len(transactions)} | Total: {total:.2f} EUR",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 20))

        if transactions:
            data = [["Date", "Description", "Montant", "Type", "Compte"]]
            for t in transactions:
                desc = t.libelle or ""
                if len(desc) > 40:
                    desc = desc[:40] + "..."
                data.append(
                    [
                        (
                            t.date_heure_transaction.strftime("%d/%m/%Y")
                            if t.date_heure_transaction
                            else ""
                        ),
                        desc,
                        f"{t.montant:.2f} EUR",
                        t.type_transaction or "",
                        (t.account.name[:20] if t.account else ""),
                    ]
                )
            table = Table(data)
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
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.beige, colors.white],
                        ),
                    ]
                )
            )
            elements.append(table)

        doc.build(elements)
        buf.seek(0)
        filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return buf.getvalue(), filename, "application/pdf"
