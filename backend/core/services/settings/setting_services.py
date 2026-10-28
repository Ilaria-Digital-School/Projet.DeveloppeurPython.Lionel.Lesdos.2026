"""
Services pour la gestion des paramètres utilisateur.
"""

import csv
import io
import json
from datetime import datetime

from openpyxl import Workbook

from core.extensions import db
from core.models.setting import UserSetting


class SettingService:
    """Service pour la gestion des paramètres utilisateur."""

    @staticmethod
    def get_user_settings(user_id, keys=None):
        """
        Récupère les paramètres d'un utilisateur.

        Args:
            user_id (int): ID de l'utilisateur
            keys (list, optional): Liste des clés à récupérer. Si None, retourne tous les paramètres.

        Returns:
            dict: Dictionnaire des paramètres {clé: valeur}
        """
        if keys is not None:
            settings = {}
            for key in keys:
                settings[key] = UserSetting.get_setting(user_id, key)
            return settings

        # Si aucune clé spécifiée, retourne tous les paramètres de l'utilisateur
        settings = UserSetting.query.filter_by(user_id=user_id).all()
        return {s.key: s.get_value() for s in settings}

    @staticmethod
    def set_user_setting(user_id, key, value):
        """
        Définit un paramètre utilisateur.

        Args:
            user_id (int): ID de l'utilisateur
            key (str): Clé du paramètre
            value: Valeur du paramètre

        Returns:
            UserSetting: L'objet UserSetting créé ou mis à jour
        """
        return UserSetting.set_setting(user_id, key, value)

    @staticmethod
    def delete_user_setting(user_id, key):
        """
        Supprime un paramètre utilisateur.

        Args:
            user_id (int): ID de l'utilisateur
            key (str): Clé du paramètre à supprimer

        Returns:
            bool: True si supprimé, False sinon
        """
        setting = UserSetting.query.filter_by(user_id=user_id, key=key).first()
        if setting:
            db.session.delete(setting)
            db.session.commit()
            return True
        return False

    @staticmethod
    def export_user_data(user_id, export_format="json", include_attachments=True):
        """
        Exporte les données utilisateur dans le format spécifié.

        Args:
            user_id (int): ID de l'utilisateur
            export_format (str): Format d'export ('json', 'csv', 'excel')
            include_attachments (bool): Inclure les pièces jointes si True

        Returns:
            tuple: (données, nom_fichier, type_mime)
        """
        from core.models.account import Account
        from core.models.category import Category
        from core.models.transactions import Transaction
        from core.models.user import User

        # Récupérer les données de l'utilisateur
        user = db.get_or_404(User, user_id)

        # Préparer les données à exporter
        export_data = {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
            "settings": SettingService.get_user_settings(user_id),
            "accounts": [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "balance": float(acc.balance) if acc.balance is not None else None,
                    "currency": acc.currency,
                    "type": acc.account_type,
                    "created_at": (
                        acc.created_at.isoformat() if acc.created_at else None
                    ),
                    "updated_at": (
                        acc.updated_at.isoformat() if acc.updated_at else None
                    ),
                }
                for acc in Account.query.filter_by(user_id=user_id).all()
            ],
            "categories": [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description,
                    "type": cat.category_type,
                    "color": cat.color,
                    "icon": cat.icon,
                    "created_at": (
                        cat.created_at.isoformat() if cat.created_at else None
                    ),
                    "updated_at": (
                        cat.updated_at.isoformat() if cat.updated_at else None
                    ),
                }
                for cat in Category.query.filter_by(user_id=user_id).all()
            ],
            "transactions": [
                {
                    "id": txn.id,
                    "account_id": txn.account_id,
                    "category_id": txn.category_id,
                    "amount": float(txn.montant) if txn.montant is not None else None,
                    "description": txn.libelle,
                    "date": (
                        txn.date_heure_transaction.isoformat()
                        if txn.date_heure_transaction
                        else None
                    ),
                    "type": txn.type_transaction,
                    "notes": txn.notes,
                    "created_at": (
                        txn.date_creation.isoformat() if txn.date_creation else None
                    ),
                    "updated_at": (
                        txn.date_mise_a_jour.isoformat()
                        if txn.date_mise_a_jour
                        else None
                    ),
                }
                for txn in Transaction.query.filter_by(user_id=user_id).all()
            ],
        }

        # Générer le fichier d'export
        filename = f"budget_export_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if export_format == "json":
            output = io.BytesIO()
            output.write(
                json.dumps(export_data, indent=2, ensure_ascii=False).encode("utf-8")
            )
            output.seek(0)
            return output, f"{filename}.json", "application/json"

        elif export_format == "csv":
            # Pour simplifier, nous allons créer un CSV pour chaque type de données
            output = io.BytesIO()

            # Créer un fichier ZIP contenant plusieurs fichiers CSV
            import zipfile
            from io import BytesIO

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Ajouter chaque ensemble de données comme un fichier CSV séparé
                for data_type in ["user", "accounts", "categories", "transactions"]:
                    if data_type == "user":
                        # Pour l'utilisateur, créer un fichier avec une seule ligne
                        csv_data = [export_data["user"]]
                    else:
                        csv_data = export_data[data_type]

                    if not csv_data:
                        continue

                    # Convertir en CSV (le module csv ecrit du texte, pas des octets)
                    output_csv = io.StringIO()
                    if csv_data:
                        fieldnames = list(csv_data[0].keys())
                        writer = csv.DictWriter(
                            output_csv,
                            fieldnames=fieldnames,
                            quoting=csv.QUOTE_NONNUMERIC,
                        )
                        writer.writeheader()
                        writer.writerows(csv_data)

                        # Ajouter au ZIP
                        zip_file.writestr(f"{data_type}.csv", output_csv.getvalue())

            zip_buffer.seek(0)
            return zip_buffer, f"{filename}.zip", "application/zip"

        elif export_format == "excel":
            wb = Workbook()

            # Feuille Utilisateur
            ws_user = wb.active
            ws_user.title = "User"
            if export_data["user"]:
                ws_user.append(list(export_data["user"].keys()))
                ws_user.append(list(export_data["user"].values()))

            # Feuille Comptes
            if export_data["accounts"]:
                ws_accounts = wb.create_sheet("Accounts")
                ws_accounts.append(list(export_data["accounts"][0].keys()))
                for account in export_data["accounts"]:
                    ws_accounts.append(list(account.values()))

            # Feuille Catégories
            if export_data["categories"]:
                ws_categories = wb.create_sheet("Categories")
                ws_categories.append(list(export_data["categories"][0].keys()))
                for category in export_data["categories"]:
                    ws_categories.append(list(category.values()))

            # Feuille Transactions
            if export_data["transactions"]:
                ws_transactions = wb.create_sheet("Transactions")
                ws_transactions.append(list(export_data["transactions"][0].keys()))
                for transaction in export_data["transactions"]:
                    ws_transactions.append(list(transaction.values()))

            # Sauvegarder dans un buffer
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

            return (
                output,
                f"{filename}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        raise ValueError(f"Format d'export non supporté: {export_format}")
