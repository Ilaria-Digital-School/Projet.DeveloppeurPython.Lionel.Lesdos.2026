"""
API REST v1 — Comptes bancaires.

Routes:
    GET    /api/v1/comptes              Liste des comptes
    POST   /api/v1/comptes              Créer un compte
    GET    /api/v1/comptes/<id>         Détail d'un compte
    PUT    /api/v1/comptes/<id>         Modifier un compte
    DELETE /api/v1/comptes/<id>         Supprimer un compte
    POST   /api/v1/comptes/import       Importer des données
    GET    /api/v1/comptes/export       Exporter des données
"""

import csv
import io
import logging
from datetime import datetime
from decimal import Decimal

from flask import make_response, request
from flask_login import current_user, login_required

from core.extensions import db
from core.models.account import Account
from core.services.accounts.account_services import AccountService
from shared.exceptions import ConflictError, ValidationError

from . import api_v1_bp
from .auth import auth_limiter
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


@api_v1_bp.route("/comptes", methods=["GET"])
@login_required
def list_comptes():
    """Retourne la liste des comptes de l'utilisateur."""
    try:
        accounts = Account.query.filter_by(user_id=current_user.id).all()

        accounts_data = []
        for account in accounts:
            accounts_data.append(
                {
                    "id": account.id,
                    "name": account.name,
                    "account_type": account.account_type,
                    "balance": float(account.balance),
                    "currency": account.currency,
                    "is_active": account.is_active,
                    "bank_name": account.bank_name,
                    "account_number": account.account_number,
                    "iban": account.iban,
                    "bic_swift": account.bic_swift,
                }
            )

        return api_success({"accounts": accounts_data})

    except Exception as e:
        logger.error(f"Erreur liste comptes: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/comptes", methods=["POST"])
@login_required
@auth_limiter.limit("10 per minute")
def create_compte():
    """Crée un nouveau compte bancaire."""
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        if not data:
            return api_error("Données requises", 400)

        name = (data.get("name") or "").strip()
        if not name:
            return api_error("Le nom du compte est obligatoire", 400)

        account_data = {
            "name": name,
            "account_type": data.get("account_type") or data.get("type", "checking"),
            "initial_balance": Decimal(
                str(data.get("initial_balance") or data.get("balance", 0))
            ),
            "overdraft_limit": Decimal(str(data.get("overdraft_limit") or 0)),
            "currency": data.get("currency", "EUR"),
            "bank_name": (data.get("bank_name") or "").strip() or None,
            "account_number": (data.get("account_number") or "").strip() or None,
            "iban": (data.get("iban") or "").strip() or None,
            "bic_swift": (data.get("bic_swift") or "").strip() or None,
            "is_active": data.get("is_active", True),
            "notes": None,
        }

        account = AccountService.create_account(current_user.id, account_data)

        return api_success(
            {
                "account_id": account.id,
                "message": f"Le compte '{account.name}' a été créé avec succès.",
            },
            status_code=201,
        )

    except ValidationError as e:
        return api_error(str(e), 400)
    except ConflictError as e:
        return api_error(str(e), 409)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur création compte: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/comptes/<int:account_id>", methods=["GET"])
@login_required
def get_compte(account_id):
    """Retourne les données complètes d'un compte."""
    try:
        account = Account.query.filter_by(
            id=account_id, user_id=current_user.id
        ).first()
        if not account:
            return api_error("Compte non trouvé ou accès non autorisé", 404)

        account_data = {
            "id": account.id,
            "name": account.name if hasattr(account, "name") else "",
            "account_type": (
                account.account_type if hasattr(account, "account_type") else "checking"
            ),
            "balance": (
                float(account.balance)
                if hasattr(account, "balance") and account.balance
                else 0.0
            ),
            "overdraft_limit": float(account.overdraft_limit),
            "currency": account.currency if hasattr(account, "currency") else "EUR",
            "bank_name": account.bank_name if hasattr(account, "bank_name") else None,
            "account_number": (
                account.account_number if hasattr(account, "account_number") else None
            ),
            "iban": account.iban if hasattr(account, "iban") else None,
            "bic_swift": account.bic_swift if hasattr(account, "bic_swift") else None,
            "is_active": account.is_active if hasattr(account, "is_active") else True,
            "created_at": (
                account.created_at.isoformat()
                if hasattr(account, "created_at") and account.created_at
                else None
            ),
            "updated_at": (
                account.updated_at.isoformat()
                if hasattr(account, "updated_at") and account.updated_at
                else None
            ),
        }

        return api_success({"account": account_data})

    except Exception as e:
        logger.error(f"Erreur récupération compte {account_id}: {e}", exc_info=True)
        return api_error("Erreur lors de la récupération des données du compte", 500)


@api_v1_bp.route("/comptes/<int:account_id>", methods=["PUT"])
@login_required
def update_compte(account_id):
    """Met à jour un compte bancaire."""
    try:
        account = Account.query.filter_by(
            id=account_id, user_id=current_user.id
        ).first()
        if not account:
            return api_error("Compte non trouvé ou accès non autorisé", 404)

        # silent=True : ne pas lever 415 quand le client envoie du FormData
        data = request.get_json(silent=True) or request.form.to_dict()
        if not data:
            return api_error("Données requises", 400)

        name = (data.get("name") or "").strip()
        if not name:
            return api_error("Le nom du compte est obligatoire", 400)

        # Un champ absent vaut None : AccountService.update_account ignore les None,
        # le champ conserve donc sa valeur actuelle (mise à jour partielle en JSON)
        raw_balance = data.get("initial_balance", data.get("balance"))
        if raw_balance is None:
            balance = None
        else:
            try:
                balance = Decimal(str(raw_balance))
            except Exception:
                return api_error("Solde invalide", 400)

        raw_overdraft = data.get("overdraft_limit")
        if raw_overdraft in (None, ""):
            overdraft_limit = None
        else:
            try:
                overdraft_limit = Decimal(str(raw_overdraft))
            except Exception:
                return api_error("Découvert autorisé invalide", 400)

        if request.is_json:
            is_active = data.get("is_active", account.is_active)
            if isinstance(is_active, str):
                is_active = is_active.lower() not in ("false", "0", "off", "")
        else:
            # FormData : une case décochée n'est pas envoyée du tout
            is_active = data.get("is_active", "").lower() not in (
                "false",
                "0",
                "off",
                "",
            )

        update_data = {
            "name": name,
            "account_type": data.get("account_type") or None,
            "balance": balance,
            "overdraft_limit": overdraft_limit,
            "currency": data.get("currency") or None,
            "bank_name": (data.get("bank_name") or "").strip() or None,
            "account_number": (data.get("account_number") or "").strip() or None,
            "iban": (data.get("iban") or "").strip() or None,
            "bic_swift": (data.get("bic_swift") or data.get("bic") or "").strip()
            or None,
            "is_active": bool(is_active),
        }

        account = AccountService.update_account(
            account_id, current_user.id, update_data
        )

        return api_success(
            message=f"Le compte '{account.name}' a été mis à jour avec succès."
        )

    except ConflictError as e:
        return api_error(str(e), 409)
    except ValidationError as e:
        return api_error(str(e), 400)
    except Exception as e:
        logger.error(f"Erreur modification compte {account_id}: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/comptes/<int:account_id>", methods=["DELETE"])
@login_required
def delete_compte(account_id):
    """Supprime un compte bancaire."""
    try:
        account = Account.query.filter_by(
            id=account_id, user_id=current_user.id
        ).first()
        if not account:
            return api_error("Compte non trouvé ou accès non autorisé", 404)

        account_name = account.name
        AccountService.delete_account(account_id, current_user.id)

        return api_success(
            message=f"Le compte '{account_name}' a été supprimé avec succès."
        )

    except Exception as e:
        logger.error(f"Erreur suppression compte {account_id}: {e}", exc_info=True)
        return api_error("Erreur lors de la suppression du compte", 500)


@api_v1_bp.route("/comptes/import", methods=["POST"])
@login_required
@auth_limiter.limit("5 per minute")
def import_comptes():
    """Importe un relevé bancaire CSV dans un compte.

    Format : Date;Ref;Débit;Crédit;Libellé;Solde (une ligne d'en-tête).
    Tout ou rien : la moindre ligne invalide annule l'import (400 + "errors").
    dry_run=true valide le fichier et compte les lignes sans rien enregistrer.
    """
    try:
        from core.models.transactions import Transaction

        if "file" not in request.files:
            return api_error("Aucun fichier sélectionné", 400)
        file = request.files["file"]
        if file.filename == "":
            return api_error("Aucun fichier sélectionné", 400)

        # Seul le CSV est lu : .xlsx/.xls étaient acceptés puis lus comme du
        # texte (aucune transaction, mais "Import réalisé avec succès")
        if not file.filename.lower().endswith(".csv"):
            return api_error(
                "Format non supporté : seul le format CSV est pris en charge", 400
            )

        max_size = 10 * 1024 * 1024
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > max_size:
            return api_error("Le fichier est trop volumineux (maximum 10MB)", 400)

        account_id = request.form.get("account_id")
        dry_run = request.form.get("dry_run", "false").lower() == "true"
        if not account_id:
            return api_error("Compte cible requis", 400)
        try:
            account_id = int(account_id)
        except ValueError:
            return api_error("Compte cible invalide", 400)
        target_account = Account.query.filter_by(
            id=account_id, user_id=current_user.id
        ).first()
        if not target_account:
            return api_error("Compte non trouvé ou accès non autorisé", 404)

        brut = file.read()
        try:
            content = brut.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Encodage courant des exports bancaires français
            content = brut.decode("iso-8859-1")
        lines = [l for l in content.strip().splitlines()[1:] if l.strip()]
        if not lines:
            return api_error("Le fichier ne contient aucune ligne à importer", 400)

        created_transactions = 0
        balance_delta = Decimal("0")
        errors = []

        for line_num, line in enumerate(lines, start=2):
            fields = line.split(";")
            if len(fields) < 6:
                errors.append(f"Ligne {line_num}: Nombre de colonnes insuffisant")
                continue

            date_str = fields[0].strip().strip('"')
            debit_str = fields[2].strip().strip('"').replace(" ", "").replace(",", ".")
            credit_str = fields[3].strip().strip('"').replace(" ", "").replace(",", ".")
            libelle = fields[4].strip().strip('"')

            transaction_date = None
            for date_fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
                try:
                    transaction_date = datetime.strptime(date_str, date_fmt).date()
                    break
                except ValueError:
                    continue
            if not transaction_date:
                errors.append(f"Ligne {line_num}: Format de date invalide: {date_str}")
                continue

            try:
                if debit_str:
                    montant, type_transaction = abs(Decimal(debit_str)), "expense"
                elif credit_str:
                    montant, type_transaction = abs(Decimal(credit_str)), "income"
                else:
                    errors.append(f"Ligne {line_num}: Aucun montant trouvé")
                    continue
            except ArithmeticError:
                errors.append(f"Ligne {line_num}: Montant invalide")
                continue
            if montant == 0:
                errors.append(f"Ligne {line_num}: Montant nul")
                continue

            # Montant positif + statut 'completed', comme partout ailleurs :
            # le sens est porté par le type
            db.session.add(
                Transaction(
                    user_id=current_user.id,
                    account_id=account_id,
                    montant=montant,
                    type_transaction=type_transaction,
                    libelle=libelle[:200] or "Import relevé",
                    date_heure_transaction=datetime.combine(
                        transaction_date, datetime.min.time()
                    ),
                    date_valeur=transaction_date,
                    statut="completed",
                )
            )
            created_transactions += 1
            balance_delta += montant if type_transaction == "income" else -montant

        # Tout ou rien : avant, les lignes valides étaient enregistrées malgré
        # les erreurs, et l'interface affichait un succès
        if errors:
            db.session.rollback()
            return api_error(
                "Import annulé : aucune transaction importée. "
                "Corrigez les erreurs puis réessayez.",
                400,
                errors=errors,
            )

        if dry_run:
            db.session.rollback()
        else:
            db.session.flush()
            db.session.execute(
                db.text(
                    'UPDATE "ComptesBancaires" SET solde_actuel = solde_actuel + :amount '
                    "WHERE id_compte = :account_id AND utilisateur_id = :user_id"
                ),
                {
                    "amount": balance_delta,
                    "account_id": account_id,
                    "user_id": current_user.id,
                },
            )
            db.session.commit()

        return api_success(
            {
                "result": {
                    "imported_rows": len(lines),
                    "errors": [],
                    "created_transactions": created_transactions,
                    "updated_accounts": 0 if dry_run else 1,
                },
                "message": (
                    f"Simulation : {created_transactions} transaction(s) seraient importées"
                    if dry_run
                    else f"{created_transactions} transaction(s) importée(s)"
                ),
            }
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur import comptes: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/comptes/export", methods=["GET"])
@login_required
def export_comptes():
    """Exporte les données de comptes/transactions en CSV."""
    try:
        account_id = request.args.get("account_id")
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        format_type = request.args.get("format", "csv")
        include_transactions = request.args.get("include_transactions", "0") in [
            "1",
            "true",
            "True",
        ]
        include_details = request.args.get("include_account_details", "0") in [
            "1",
            "true",
            "True",
        ]

        if format_type not in ["csv", "excel"]:
            return api_error("Format non supporté. Utilisez csv ou excel.", 400)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        account_name = "tous_comptes"
        if account_id:
            try:
                acct = Account.query.filter_by(
                    id=int(account_id), user_id=current_user.id
                ).first()
                if acct:
                    account_name = (
                        "".join(
                            c for c in acct.name if c.isalnum() or c in (" ", "-", "_")
                        )
                        .strip()
                        .replace(" ", "_")
                    )
            except ValueError, AttributeError:
                pass

        filename = f"export_{account_name}_{timestamp}.{format_type if format_type == 'csv' else 'xlsx'}"

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)

        if include_transactions:
            from core.models.category import Category
            from core.models.transactions import Transaction

            headers = [
                "Date",
                "Compte",
                "Libelle",
                "Montant",
                "Devise",
                "Type_Transaction",
                "Categorie",
                "Statut",
                "Compte_Destination",
            ]
            if include_details:
                headers.extend(["Frais", "Note", "Reference"])
            writer.writerow(headers)

            tq = Transaction.query.filter_by(user_id=current_user.id)
            if account_id:
                tq = tq.filter_by(account_id=int(account_id))
            if date_from:
                try:
                    tq = tq.filter(
                        Transaction.date_heure_transaction
                        >= datetime.strptime(date_from, "%Y-%m-%d")
                    )
                except ValueError:
                    pass
            if date_to:
                try:
                    dt = datetime.strptime(date_to, "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59
                    )
                    tq = tq.filter(Transaction.date_heure_transaction <= dt)
                except ValueError:
                    pass

            transactions = tq.order_by(Transaction.date_heure_transaction.desc()).all()

            # Pré-charger les comptes et catégories de l'utilisateur pour éviter N+1
            user_accounts = {
                a.id: a for a in Account.query.filter_by(user_id=current_user.id).all()
            }
            user_categories = {
                c.id: c for c in Category.query.filter_by(user_id=current_user.id).all()
            }

            for t in transactions:
                acct_obj = user_accounts.get(t.account_id)
                cat_name = ""
                if t.category_id:
                    cat = user_categories.get(t.category_id)
                    cat_name = cat.name if cat else ""
                dest = ""
                if hasattr(t, "destination_account_id") and t.destination_account_id:
                    d = user_accounts.get(t.destination_account_id)
                    dest = d.name if d else ""

                row = [
                    (
                        t.date_heure_transaction.strftime("%Y-%m-%d")
                        if t.date_heure_transaction
                        else ""
                    ),
                    acct_obj.name if acct_obj else "Inconnu",
                    t.libelle or "",
                    float(t.montant),
                    acct_obj.currency if acct_obj else "EUR",
                    t.type_transaction or "",
                    cat_name,
                    t.statut or "",
                    dest,
                ]
                if include_details:
                    row.extend(
                        [
                            float(t.frais_transaction) if t.frais_transaction else 0,
                            getattr(t, "note", "") or "",
                            getattr(t, "reference", "") or "",
                        ]
                    )
                writer.writerow(row)
        else:
            headers = ["Compte", "Type", "Solde", "Devise", "Banque"]
            if include_details:
                headers.extend(["IBAN", "BIC", "Numero_Compte"])
            writer.writerow(headers)

            query = Account.query.filter_by(user_id=current_user.id)
            if account_id:
                query = query.filter_by(id=int(account_id))
            for acct in query.all():
                row = [
                    acct.name,
                    acct.account_type,
                    float(acct.balance),
                    acct.currency,
                    acct.bank_name or "",
                ]
                if include_details:
                    row.extend(
                        [
                            acct.iban or "",
                            acct.bic_swift or "",
                            acct.account_number or "",
                        ]
                    )
                writer.writerow(row)

        csv_data = output.getvalue()
        output.close()

        response = make_response(csv_data)
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        logger.error(f"Erreur export comptes: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
