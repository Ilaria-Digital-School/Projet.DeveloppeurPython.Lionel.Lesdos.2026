"""
API REST v1 — Transactions.

Routes:
    GET    /api/v1/transactions              Liste des transactions (filtrée/paginée)
    POST   /api/v1/transactions              Créer une transaction
    GET    /api/v1/transactions/<id>         Détail d'une transaction
    PUT    /api/v1/transactions/<id>         Modifier une transaction
    DELETE /api/v1/transactions/<id>         Supprimer une transaction
    POST   /api/v1/transactions/bulk-delete  Suppression en lot
    POST   /api/v1/transactions/import       Importer des transactions CSV
    GET    /api/v1/transactions/export       Exporter des transactions
"""

import csv
import io
import logging
import re
from datetime import datetime
from decimal import Decimal

from flask import make_response, request
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from core.extensions import db
from core.models.transactions import TransactionType
from core.services.transactions import TransactionService
from shared.exceptions import (
    AccountNotFoundError,
    CategoryNotFoundError,
    InsufficientFundsError,
    InvalidTransactionError,
)

from . import api_v1_bp
from .auth import auth_limiter
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


# ── LIST / CREATE ────────────────────────────────────────────────────────────


@api_v1_bp.route("/transactions", methods=["GET"])
@login_required
def list_transactions():
    """Retourne la liste filtrée et paginée des transactions."""
    try:
        service = TransactionService()
        page = request.args.get("page", 1, type=int)
        per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)
        filters = {}

        account_id = request.args.get("account")
        if account_id:
            from core.models.account import Account

            acct = db.session.get(Account, int(account_id))
            if acct and acct.user_id == current_user.id:
                filters["account_id"] = int(account_id)
            else:
                return api_error("Compte non trouvé", 404)

        category_id = request.args.get("category")
        if category_id:
            from core.models.category import Category

            cat = db.session.get(Category, int(category_id))
            if cat and cat.user_id == current_user.id:
                filters["category_id"] = int(category_id)
            else:
                return api_error("Catégorie non trouvée", 404)

        transaction_type = request.args.get("type")
        if transaction_type:
            type_map = {
                "income": ["SALAIRE"],
                "expense": ["ACHAT", "expense"],
                "transfer": ["VIREMENT"],
            }
            filters["transaction_types"] = type_map.get(
                transaction_type, [transaction_type]
            )

        date_from = request.args.get("date_from")
        if date_from:
            try:
                filters["start_date"] = datetime.strptime(date_from, "%d/%m/%Y").date()
            except ValueError:
                return api_error(
                    "Format de date_from invalide (attendu: DD/MM/YYYY)", 400
                )

        date_to = request.args.get("date_to")
        if date_to:
            try:
                filters["end_date"] = datetime.strptime(date_to, "%d/%m/%Y").date()
            except ValueError:
                return api_error(
                    "Format de date_to invalide (attendu: DD/MM/YYYY)", 400
                )

        transactions, total = service.get_transactions(
            user_id=current_user.id, page=page, per_page=per_page, **filters
        )

        transactions_data = []
        for t in transactions:
            try:
                account_name = "N/A"
                if hasattr(t, "account") and t.account:
                    account_name = getattr(t.account, "name", "N/A")
                category_name = None
                if hasattr(t, "category") and t.category:
                    category_name = getattr(t.category, "name", None)

                transactions_data.append(
                    {
                        "id": t.id,
                        "date": (
                            t.date_heure_transaction.strftime("%d/%m/%Y")
                            if t.date_heure_transaction
                            else ""
                        ),
                        "description": t.libelle or "",
                        "amount": float(t.montant) if t.montant else 0.0,
                        "type": (
                            str(t.type_transaction) if t.type_transaction else "unknown"
                        ),
                        "account": account_name,
                        "category": category_name,
                        "notes": t.notes or "",
                    }
                )
            except Exception as item_error:
                logger.error(f"Erreur traitement transaction {t.id}: {item_error}")

        return api_success(
            {
                "transactions": transactions_data,
                "pagination": {"page": page, "total": total},
            }
        )

    except (ValueError, KeyError) as e:
        return api_error(f"Paramètre invalide: {e}", 400)
    except SQLAlchemyError as e:
        logger.error(f"Erreur DB liste transactions: {e}", exc_info=True)
        return api_error("Erreur de base de données", 500)
    except Exception as e:
        logger.error(f"Erreur liste transactions: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/transactions", methods=["POST"])
@login_required
@auth_limiter.limit("30 per minute")
def create_transaction():
    """Crée une nouvelle transaction."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Données JSON requises", 400)

        required_fields = ["type", "amount", "date", "description", "account_id"]
        for field in required_fields:
            if field not in data:
                return api_error(f"Champ requis manquant: {field}", 400)

        service = TransactionService()

        # Parser la date
        date_str = data["date"]
        transaction_datetime = None
        try:
            if " " in date_str and ":" in date_str:
                transaction_datetime = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:
                base_date = datetime.strptime(date_str, "%Y-%m-%d")
                now = datetime.now()
                if base_date.date() == now.date():
                    transaction_datetime = now
                else:
                    transaction_datetime = base_date.replace(
                        hour=12, minute=0, second=0
                    )
        except ValueError:
            transaction_datetime = datetime.now()

        transaction_data = {
            "user_id": current_user.id,
            "account_id": int(data["account_id"]),
            "amount": Decimal(str(abs(float(data["amount"])))),
            "transaction_type": data["type"],
            "description": data["description"],
            "transaction_datetime": transaction_datetime,
            "category_id": (
                int(data["category_id"]) if data.get("category_id") else None
            ),
            "destination_account_id": (
                int(data["destination_account_id"])
                if data.get("destination_account_id")
                else None
            ),
            "notes": data.get("notes", ""),
            "status": "completed",
        }

        transaction = service.create_transaction(**transaction_data)
        if transaction:
            return api_success(
                {
                    "transaction_id": transaction.id,
                    "message": "Transaction créée avec succès",
                },
                status_code=201,
            )
        return api_error("Erreur lors de la création de la transaction", 500)

    except ValueError:
        return api_error("Erreur de validation des données", 400)
    except (
        InsufficientFundsError,
        AccountNotFoundError,
        CategoryNotFoundError,
        InvalidTransactionError,
    ) as e:
        return api_error(str(e), getattr(e, "status_code", 400))
    except Exception as e:
        logger.error(f"Erreur création transaction: {e}", exc_info=True)
        return api_error("Erreur interne du serveur", 500)


# ── DETAIL / UPDATE / DELETE ─────────────────────────────────────────────────


@api_v1_bp.route("/transactions/<int:transaction_id>", methods=["GET"])
@login_required
def get_transaction(transaction_id):
    """Retourne le détail d'une transaction."""
    try:
        service = TransactionService()
        transaction = service.get_transaction_by_id(transaction_id, current_user.id)
        if not transaction:
            return api_error("Transaction non trouvée", 404)

        t_type = (transaction.type_transaction or "").lower()
        if t_type in ("salaire", "revenu_autre", "remboursement"):
            generic_type = "income"
        elif t_type in ("achat", "expense", "loyer", "facture", "abonnement"):
            generic_type = "expense"
        elif t_type in ("virement", "prelevement"):
            generic_type = "transfer"
        else:
            generic_type = "expense"

        return api_success(
            {
                "id": transaction.id,
                "date": transaction.date_heure_transaction.strftime("%d/%m/%Y"),
                "description": transaction.libelle,
                "amount": float(transaction.montant),
                "type": generic_type,
                "account_id": transaction.account_id,
                "category_id": transaction.category_id,
                "notes": transaction.notes or "",
                "destination_account_id": transaction.destination_account_id,
            }
        )

    except SQLAlchemyError as e:
        logger.error(
            f"Erreur DB récupération transaction {transaction_id}: {e}", exc_info=True
        )
        return api_error("Erreur de base de données", 500)
    except Exception as e:
        logger.error(
            f"Erreur récupération transaction {transaction_id}: {e}", exc_info=True
        )
        return api_error("Erreur interne du serveur", 500)


@api_v1_bp.route("/transactions/<int:transaction_id>", methods=["PUT"])
@login_required
def update_transaction(transaction_id):
    """Modifie une transaction existante."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Données JSON requises", 400)

        required_fields = ["amount", "account_id", "date"]
        for field in required_fields:
            if field not in data:
                return api_error(f"Champ requis manquant: {field}", 400)

        service = TransactionService()

        # Parser la date (accepte "AAAA-MM-JJ HH:MM:SS" comme "AAAA-MM-JJ",
        # cohérent avec la route de création — le frontend envoie l'heure)
        date_str = data["date"]
        try:
            if " " in date_str and ":" in date_str:
                date_heure_transaction = datetime.strptime(
                    date_str, "%Y-%m-%d %H:%M:%S"
                )
            else:
                date_heure_transaction = datetime.strptime(
                    date_str, "%Y-%m-%d"
                ).replace(hour=12)
        except ValueError:
            return api_error("Format de date invalide", 400)

        update_data = {
            "libelle": data.get("description"),
            "montant": Decimal(str(abs(float(data["amount"])))),
            "type_transaction": data.get("type"),
            "account_id": int(data["account_id"]),
            "category_id": (
                int(data["category_id"]) if data.get("category_id") else None
            ),
            "notes": data.get("notes", ""),
            "date_heure_transaction": date_heure_transaction,
        }

        result = service.update_transaction(
            transaction_id, current_user.id, **update_data
        )
        if result:
            return api_success(message="Transaction modifiée avec succès")
        return api_error("Transaction non trouvée ou accès non autorisé", 404)

    except (ValueError, KeyError) as e:
        return api_error(f"Données invalides: {e}", 400)
    except SQLAlchemyError as e:
        logger.error(
            f"Erreur DB modification transaction {transaction_id}: {e}", exc_info=True
        )
        return api_error("Erreur de base de données", 500)
    except Exception as e:
        logger.error(
            f"Erreur modification transaction {transaction_id}: {e}", exc_info=True
        )
        return api_error("Erreur interne du serveur", 500)


@api_v1_bp.route("/transactions/<int:transaction_id>", methods=["DELETE"])
@login_required
def delete_transaction(transaction_id):
    """Supprime une transaction."""
    try:
        service = TransactionService()
        result = service.delete_transaction(transaction_id, current_user.id)
        if result:
            return api_success(message="Transaction supprimée avec succès")
        return api_error("Transaction non trouvée ou accès non autorisé", 404)

    except SQLAlchemyError as e:
        logger.error(
            f"Erreur DB suppression transaction {transaction_id}: {e}", exc_info=True
        )
        return api_error("Erreur de base de données", 500)
    except Exception as e:
        logger.error(
            f"Erreur suppression transaction {transaction_id}: {e}", exc_info=True
        )
        return api_error("Erreur interne du serveur", 500)


# ── BULK DELETE ──────────────────────────────────────────────────────────────


@api_v1_bp.route("/transactions/bulk-delete", methods=["POST"])
@login_required
@auth_limiter.limit("10 per minute")
def bulk_delete_transactions():
    """Supprime plusieurs transactions en une fois."""
    try:
        data = request.get_json()
        if not data or "transaction_ids" not in data:
            return api_error("Liste des IDs de transactions requise", 400)

        transaction_ids = data["transaction_ids"]
        if not isinstance(transaction_ids, list) or len(transaction_ids) == 0:
            return api_error("Liste d'IDs non valide ou vide", 400)

        MAX_BULK_DELETE = 200
        if len(transaction_ids) > MAX_BULK_DELETE:
            return api_error(f"Maximum {MAX_BULK_DELETE} suppressions par requête", 400)

        service = TransactionService()
        deleted_count = 0
        errors = []

        for tid in transaction_ids:
            try:
                tid = int(tid)
                if service.delete_transaction(tid, current_user.id):
                    deleted_count += 1
                else:
                    errors.append(f"Transaction {tid} non trouvée")
            except ValueError:
                errors.append(f"ID invalide: {tid}")
            except Exception as e:
                errors.append(f"Erreur pour {tid}: {e}")

        resp = {
            "deleted_count": deleted_count,
            "total_requested": len(transaction_ids),
            "message": f"{deleted_count} transaction(s) supprimée(s)",
        }
        if errors:
            resp["errors"] = errors

        return api_success(resp)

    except SQLAlchemyError as e:
        logger.error(f"Erreur DB suppression en lot: {e}", exc_info=True)
        return api_error("Erreur de base de données", 500)
    except Exception as e:
        logger.error(f"Erreur suppression en lot: {e}", exc_info=True)
        return api_error("Erreur interne du serveur", 500)


# ── IMPORT ───────────────────────────────────────────────────────────────────


@api_v1_bp.route("/transactions/import", methods=["POST"])
@login_required
@auth_limiter.limit("5 per minute")
def import_transactions():
    """Importe des transactions depuis un fichier CSV."""
    try:
        if "file" not in request.files:
            return api_error("Aucun fichier fourni", 400)

        file = request.files["file"]
        if file.filename == "" or not file.filename.lower().endswith(".csv"):
            return api_error("Fichier CSV requis", 400)

        file_content = file.read()
        try:
            content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = file_content.decode("iso-8859-1")
            except UnicodeDecodeError:
                return api_error("Encodage non supporté", 400)

        def smart_get_column(row, *names):
            for name in names:
                if name in row and row[name]:
                    return row[name].strip()
                for key in row.keys():
                    if key.lower().strip() == name.lower().strip() and row[key]:
                        return row[key].strip()
            return ""

        sample = content.split("\n")[0] if content else ""
        delimiter = ";"
        if sample.count(",") > sample.count(";"):
            delimiter = ","
        elif sample.count("\t") > sample.count(";"):
            delimiter = "\t"

        csv_reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        imported_count = 0
        errors = []
        service = TransactionService()
        MAX_ROWS = 5000

        def parse_montant(valeur):
            """'1 234,56 €', '-50,00', '1,234.56' -> Decimal."""
            clean = valeur.replace(" ", "").replace("€", "").replace("$", "")
            if "," in clean and "." in clean:
                if clean.rindex(",") > clean.rindex("."):
                    clean = clean.replace(".", "").replace(",", ".")
                else:
                    clean = clean.replace(",", "")
            elif "," in clean:
                if len(clean.split(",")[-1]) <= 2:
                    clean = clean.replace(",", ".")
                else:
                    clean = clean.replace(",", "")
            clean = re.sub(r"[^\d.\-]", "", clean)
            return Decimal(clean)

        # Catégories de l'utilisateur, par nom insensible à la casse
        # (create_transaction n'accepte que les catégories de l'utilisateur)
        from core.models.category import Category

        categories = {
            c.name.strip().lower(): c.id
            for c in Category.query.filter_by(user_id=current_user.id).all()
        }
        warnings = []

        # Types précis reconnus tels quels (ceux que l'export écrit : loyer, facture...)
        types_connus = {
            v.lower()
            for v in TransactionType.income_values() + TransactionType.expense_values()
        }

        def sanitize(value, max_length=500):
            if not value:
                return value
            value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
            value = value.lstrip("=+@|")
            return value[:max_length]

        for row_num, row in enumerate(csv_reader, start=2):
            if row_num - 1 > MAX_ROWS:
                errors.append(f"Import limité à {MAX_ROWS} lignes")
                break
            try:
                date_str = smart_get_column(
                    row, "Date", "date", "DATE", "Date_Transaction"
                )
                if not date_str:
                    errors.append(f"Ligne {row_num}: Date manquante")
                    continue

                transaction_date = None
                for fmt in [
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%Y %H:%M",
                    "%d/%m/%Y",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%d-%m-%Y",
                    "%d.%m.%Y",
                ]:
                    try:
                        transaction_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                if not transaction_date:
                    errors.append(
                        f"Ligne {row_num}: Format de date non reconnu '{date_str}'"
                    )
                    continue

                description = smart_get_column(
                    row, "Description", "description", "Libelle", "libelle", "Label"
                )
                if not description:
                    errors.append(f"Ligne {row_num}: Description manquante")
                    continue

                montant_str = smart_get_column(
                    row, "Montant", "montant", "Amount", "amount", "Value", "Total"
                )
                if not montant_str:
                    errors.append(f"Ligne {row_num}: Montant manquant")
                    continue

                amount = parse_montant(montant_str)

                t_type_str = smart_get_column(row, "Type", "type", "TYPE").lower()
                if t_type_str in ("revenu", "income", "credit"):
                    t_type = "income"
                elif t_type_str in (
                    "depense",
                    "d\u00e9pense",
                    "expense",
                    "debit",
                    "d\u00e9bit",
                ):
                    t_type = "expense"
                elif t_type_str in TransactionType.transfer_values():
                    t_type = "virement"
                elif t_type_str in types_connus:
                    t_type = t_type_str
                else:
                    t_type = "income" if amount >= 0 else "expense"
                # Le sens est port\u00e9 par le type : les relev\u00e9s notent souvent les d\u00e9bits en n\u00e9gatif
                amount = abs(amount)

                frais_str = smart_get_column(row, "Frais", "frais", "Fees", "fees")
                fees = abs(parse_montant(frais_str)) if frais_str else Decimal("0.00")

                from core.models.account import Account

                acct_name = smart_get_column(
                    row, "Compte", "compte", "Account", "account"
                )
                acct_id = None
                if acct_name:
                    acct = Account.query.filter_by(
                        user_id=current_user.id, name=acct_name
                    ).first()
                    if acct:
                        acct_id = acct.id
                if not acct_id:
                    acct = Account.query.filter(
                        Account.user_id == current_user.id,
                        Account._is_active_db == True,
                    ).first()
                    acct_id = acct.id if acct else None
                if not acct_id:
                    errors.append(f"Ligne {row_num}: Aucun compte disponible")
                    continue

                tx_data = {
                    "user_id": current_user.id,
                    "account_id": acct_id,
                    "amount": amount,
                    "fees": fees,
                    "transaction_type": t_type,
                    "description": sanitize(description),
                    "transaction_date": transaction_date,
                }

                # Virement interne : crédite le compte destination s'il est indiqué
                dest_name = smart_get_column(
                    row, "Compte destination", "Destination", "Destination account"
                )
                if t_type == "virement" and dest_name:
                    dest = Account.query.filter_by(
                        user_id=current_user.id, name=dest_name
                    ).first()
                    if not dest:
                        errors.append(
                            f"Ligne {row_num}: Compte destination introuvable '{dest_name}'"
                        )
                        continue
                    tx_data["destination_account_id"] = dest.id

                # Catégorie inconnue : la ligne est importée sans catégorie (avertissement)
                cat_name = smart_get_column(row, "Catégorie", "Categorie", "Category")
                if cat_name:
                    cat_id = categories.get(cat_name.lower())
                    if cat_id:
                        tx_data["category_id"] = cat_id
                    else:
                        warnings.append(
                            f"Ligne {row_num}: catégorie inconnue '{sanitize(cat_name, 100)}', "
                            "transaction importée sans catégorie"
                        )

                notes = smart_get_column(row, "Notes", "notes", "Note", "Commentaire")
                if notes:
                    tx_data["notes"] = sanitize(notes, 1000)

                # Import atomique : flush sans commit, le commit final
                # n'a lieu que si toutes les lignes sont valides
                service.create_transaction(**tx_data, commit=False)
                imported_count += 1

            except SQLAlchemyError as e:
                # Session potentiellement corrompue : abandon immédiat
                db.session.rollback()
                logger.error(f"Erreur DB import ligne {row_num}: {e}", exc_info=True)
                errors.append(f"Ligne {row_num}: erreur de base de données")
                break
            except Exception as e:
                errors.append(f"Ligne {row_num}: {e}")

        # Import tout ou rien : la moindre erreur annule l'ensemble
        if errors:
            db.session.rollback()
            return api_error(
                "Import annulé : aucune transaction importée. "
                "Corrigez les erreurs puis réessayez.",
                400,
                errors=errors,
            )

        db.session.commit()
        return api_success(
            {
                "imported_count": imported_count,
                "total_rows": csv_reader.line_num - 1,
                "message": f"{imported_count} transaction(s) importée(s)",
                "warnings": warnings,
            }
        )

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Erreur DB import transactions: {e}", exc_info=True)
        return api_error("Erreur de base de données lors de l'import", 500)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur import transactions: {e}", exc_info=True)
        return api_error("Erreur lors de l'import", 500)


# ── EXPORT ───────────────────────────────────────────────────────────────────


@api_v1_bp.route("/transactions/export", methods=["GET"])
@login_required
def export_transactions():
    """Exporte les transactions selon les filtres appliqués."""
    try:
        export_format = request.args.get("format", "csv").lower()
        if export_format not in ["csv", "xlsx", "pdf"]:
            return api_error("Format non supporté (csv, xlsx, pdf)", 400)

        filters = {}
        if request.args.get("account"):
            from core.models.account import Account

            acct = db.session.get(Account, int(request.args.get("account")))
            if acct and acct.user_id == current_user.id:
                filters["account_id"] = acct.id
            else:
                return api_error("Compte non trouvé", 404)
        if request.args.get("category"):
            from core.models.category import Category

            cat = db.session.get(Category, int(request.args.get("category")))
            if cat and cat.user_id == current_user.id:
                filters["category_id"] = cat.id
            else:
                return api_error("Catégorie non trouvée", 404)
        if request.args.get("type"):
            filters["transaction_type"] = request.args.get("type")
        if request.args.get("date_from"):
            try:
                filters["start_date"] = datetime.strptime(
                    request.args.get("date_from"), "%d/%m/%Y"
                ).date()
            except ValueError:
                return api_error("Format date_from invalide (DD/MM/YYYY)", 400)
        if request.args.get("date_to"):
            try:
                filters["end_date"] = datetime.strptime(
                    request.args.get("date_to"), "%d/%m/%Y"
                ).date()
            except ValueError:
                return api_error("Format date_to invalide (DD/MM/YYYY)", 400)

        MAX_EXPORT_ROWS = 5000
        service = TransactionService()
        transactions, _ = service.get_transactions(
            user_id=current_user.id, page=1, per_page=MAX_EXPORT_ROWS, **filters
        )

        if export_format == "csv":
            return _export_csv(transactions)
        elif export_format == "xlsx":
            return _export_excel(transactions)
        elif export_format == "pdf":
            return _export_pdf(transactions)

    except (ValueError, KeyError) as e:
        return api_error(f"Paramètre d'export invalide: {e}", 400)
    except SQLAlchemyError as e:
        logger.error(f"Erreur DB export: {e}", exc_info=True)
        return api_error("Erreur de base de données", 500)
    except Exception as e:
        logger.error(f"Erreur export: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


def _make_export_response(data, filename, content_type):
    """Construit une réponse HTTP de téléchargement de fichier."""
    resp = make_response(data)
    resp.headers["Content-Type"] = content_type
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


def _export_csv(transactions):
    from core.services.import_export.export_service import ExportService

    data, filename, content_type = ExportService.to_csv(transactions)
    return _make_export_response(data, filename, content_type)


def _export_excel(transactions):
    try:
        from core.services.import_export.export_service import ExportService

        data, filename, content_type = ExportService.to_excel(transactions)
        return _make_export_response(data, filename, content_type)
    except ImportError:
        return api_error("Export Excel non disponible (openpyxl manquant)", 500)


def _export_pdf(transactions):
    try:
        from core.services.import_export.export_service import ExportService

        data, filename, content_type = ExportService.to_pdf(transactions)
        return _make_export_response(data, filename, content_type)
    except ImportError:
        return api_error("Export PDF non disponible (reportlab manquant)", 500)
