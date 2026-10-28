"""
Services du module d'administration
Gère la logique métier liée à l'administration du système
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy import func, text

from core.extensions import db
from core.models.account import Account
from core.models.category import Category
from core.models.device import DeviceLoginHistory
from core.models.notification import Notification
from core.models.transactions import Transaction, TransactionType
from core.models.user import User
from core.security.security_2fa import generate_2fa_secret


def _format_dt(value, with_time: bool = True) -> str:
    """Formate une date (datetime ou string legacy) en jj/mm/aaaa [HH:MM].

    Retourne "N/A" si la valeur est absente. Gère les datetime Python
    et les strings legacy au format '2025-08-04 12:18:23.690338'.
    """
    if not value:
        return "N/A"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
    try:
        parts = str(value).split(" ")
        year, month, day = parts[0].split("-")
        date_str = f"{day}/{month}/{year}"
        if with_time and len(parts) > 1:
            hour_minute = parts[1].split(".")[0][:5]
            if hour_minute:
                return f"{date_str} {hour_minute}"
        return date_str
    except ValueError, IndexError, AttributeError:
        text_value = str(value)
        return text_value[:16] if with_time else text_value[:10]


def _iso(value) -> str:
    """Convertit une date en string ISO triable (chaîne vide si None)."""
    if value is None:
        return ""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class AdminService:
    """Service pour les opérations d'administration"""

    @staticmethod
    def get_dashboard_stats() -> Dict:
        """Récupère les statistiques pour le dashboard admin"""
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        try:
            # Statistiques utilisateurs
            total_users = User.query.count()
            active_users = User.query.filter_by(is_active=True).count()
            new_users_week = User.query.filter(User.created_at >= week_ago).count()

            # Statistiques comptes
            total_accounts = Account.query.count()
            active_accounts = Account.query.filter(
                Account._is_active_db == True
            ).count()

            # Statistiques transactions
            total_transactions = Transaction.query.count()
            transactions_week = Transaction.query.filter(
                Transaction.date_heure_transaction >= week_ago
            ).count()

            # Volume financier (somme des montants)
            total_volume_result = db.session.execute(
                text("SELECT COALESCE(SUM(ABS(montant)), 0) FROM transactions")
            ).scalar()
            total_volume = float(total_volume_result) if total_volume_result else 0.0

            # Volume cette semaine
            week_volume_result = db.session.execute(
                text(
                    "SELECT COALESCE(SUM(ABS(montant)), 0) FROM transactions WHERE date_heure_transaction >= :week_ago"
                ),
                {"week_ago": week_ago},
            ).scalar()
            week_volume = float(week_volume_result) if week_volume_result else 0.0

            # Catégories
            total_categories = Category.query.count()

            # Dernières activités (dernières transactions)
            recent_transactions = (
                db.session.query(Transaction, User, Account)
                .join(User, Transaction.user_id == User.id)
                .join(Account, Transaction.account_id == Account.id)
                .order_by(Transaction.date_heure_transaction.desc())
                .limit(5)
                .all()
            )

            recent_activities = []
            for trans, user, account in recent_transactions:
                recent_activities.append(
                    {
                        "id": trans.id,
                        "user": user.username,
                        "account": account.nom_banque,
                        "amount": float(trans.montant),
                        "description": trans.libelle,
                        "date": (
                            trans.date_heure_transaction.strftime("%d/%m/%Y %H:%M")
                            if hasattr(trans.date_heure_transaction, "strftime")
                            else str(trans.date_heure_transaction)
                        ),
                    }
                )

            return {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "new_week": new_users_week,
                },
                "accounts": {"total": total_accounts, "active": active_accounts},
                "transactions": {
                    "total": total_transactions,
                    "week": transactions_week,
                },
                "financial": {"total_volume": total_volume, "week_volume": week_volume},
                "categories": {"total": total_categories},
                "recent_activities": recent_activities,
            }

        except Exception as e:
            current_app.logger.error(f"Erreur lors du calcul des stats admin: {e}")
            return {
                "users": {"total": 0, "active": 0, "new_week": 0},
                "accounts": {"total": 0, "active": 0},
                "transactions": {"total": 0, "week": 0},
                "financial": {"total_volume": 0.0, "week_volume": 0.0},
                "categories": {"total": 0},
                "recent_activities": [],
            }

    @staticmethod
    def get_all_users() -> List[Dict]:
        """Récupère la liste de tous les utilisateurs"""
        try:
            # Log de débogage
            current_app.logger.info(f"🔍 Récupération de tous les utilisateurs...")

            # Vérifier d'abord le nombre d'utilisateurs
            user_count = User.query.count()
            current_app.logger.info(
                f"📊 Nombre total d'utilisateurs en base: {user_count}"
            )

            # Récupérer tous les utilisateurs
            users = User.query.all()
            current_app.logger.info(f"✅ {len(users)} utilisateurs récupérés")

            # Compteurs groupés (anti N+1) : deux requêtes pour tous les users
            acc_counts = dict(
                db.session.query(Account.user_id, func.count(Account.id))
                .group_by(Account.user_id)
                .all()
            )
            tx_counts = dict(
                db.session.query(Transaction.user_id, func.count(Transaction.id))
                .group_by(Transaction.user_id)
                .all()
            )

            result = []
            for user in users:
                try:
                    last_login_attr = getattr(user, "last_login_at", None) or getattr(
                        user, "last_login", None
                    )
                    result.append(
                        {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "is_active": user.is_active,
                            "is_admin": any(
                                role.name == "admin" for role in user.roles
                            ),
                            "roles": [role.name for role in user.roles],
                            "created_at": _format_dt(user.created_at, with_time=False),
                            "last_login": (
                                _format_dt(last_login_attr)
                                if last_login_attr
                                else "Jamais"
                            ),
                            "login_count": user.login_count or 0,
                            "two_factor_enabled": user.two_factor_enabled or False,
                            "is_locked": user.is_locked or False,
                            "last_login_ip": user.last_login_ip,
                            "avatar_url": user.avatar_url,
                            "accounts_count": acc_counts.get(user.id, 0),
                            "transactions_count": tx_counts.get(user.id, 0),
                        }
                    )
                except Exception as e:
                    current_app.logger.error(
                        f"Erreur lors du traitement de l'utilisateur {user.id}: {e}"
                    )
                    # Ajouter l'utilisateur avec des valeurs par défaut
                    result.append(
                        {
                            "id": user.id,
                            "username": user.username or "N/A",
                            "email": user.email or "N/A",
                            "is_active": user.is_active,
                            "is_admin": False,
                            "roles": [],
                            "created_at": "N/A",
                            "last_login": "Jamais",
                            "login_count": 0,
                            "two_factor_enabled": False,
                            "is_locked": False,
                            "last_login_ip": None,
                            "avatar_url": None,
                            "accounts_count": 0,
                            "transactions_count": 0,
                        }
                    )
            return result
        except Exception as e:
            current_app.logger.error(
                f"Erreur lors de la récupération des utilisateurs: {e}"
            )
            return []

    @staticmethod
    def get_user_details(user_id: int) -> Optional[Dict]:
        """Récupère les détails d'un utilisateur"""
        user = db.session.get(User, user_id)
        if not user:
            return None

        # Compter les comptes de l'utilisateur
        accounts_count = Account.query.filter_by(user_id=user_id).count()

        # Compter les transactions de l'utilisateur
        transactions_count = Transaction.query.filter_by(user_id=user_id).count()

        # Volume total des transactions
        volume_result = db.session.execute(
            text(
                "SELECT COALESCE(SUM(ABS(montant)), 0) FROM transactions WHERE user_id = :user_id"
            ),
            {"user_id": user_id},
        ).scalar()
        total_volume = float(volume_result) if volume_result else 0.0

        last_login_attr = getattr(user, "last_login_at", None) or getattr(
            user, "last_login", None
        )

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "email_verified": user.email_verified,
            "roles": [role.name for role in user.roles],
            "created_at": _format_dt(user.created_at),
            "last_login": (
                _format_dt(last_login_attr) if last_login_attr else "Jamais"
            ),
            "login_count": user.login_count or 0,
            "two_factor_enabled": user.two_factor_enabled or False,
            "accounts_count": accounts_count,
            "transactions_count": transactions_count,
            "total_volume": total_volume,
            # Profil
            "phone": user.phone,
            "city": user.city,
            "country": user.country,
            "language": user.language,
            "timezone": user.timezone,
            "avatar_url": user.avatar_url,
            # Sécurité
            "login_attempts": user.login_attempts or 0,
            "is_locked": user.is_locked or False,
            "last_login_ip": user.last_login_ip,
            "current_login_ip": user.current_login_ip,
            "two_factor_enabled_at": (
                _format_dt(user.two_factor_enabled_at)
                if user.two_factor_enabled_at
                else None
            ),
            # Cycle de vie
            "updated_at": _format_dt(user.updated_at),
            "deactivated_at": (
                _format_dt(user.deactivated_at) if user.deactivated_at else None
            ),
            "deactivation_reason": user.deactivation_reason,
        }

    @staticmethod
    def get_user_activity(user_id: int, limit: int = 20) -> Optional[List[Dict]]:
        """Récupère l'activité récente réelle d'un utilisateur.

        Fusionne connexions (DeviceLoginHistory), transactions et notifications,
        triées par date décroissante. Retourne None si l'utilisateur n'existe pas.
        """
        user = db.session.get(User, user_id)
        if not user:
            return None

        activity: List[Dict] = []

        # Connexions (index idx_login_history_user_time)
        logins = (
            DeviceLoginHistory.query.filter_by(user_id=user_id)
            .order_by(DeviceLoginHistory.login_time.desc())
            .limit(limit)
            .all()
        )
        for entry in logins:
            details_parts = [p for p in (entry.ip_address, entry.location) if p]
            activity.append(
                {
                    "type": "login",
                    "timestamp": _iso(entry.login_time),
                    "title": (
                        "Connexion réussie"
                        if entry.was_successful
                        else "Connexion échouée"
                    ),
                    "details": " — ".join(details_parts),
                    "success": bool(entry.was_successful),
                    "failure_reason": entry.failure_reason,
                    "date_display": _format_dt(entry.login_time),
                }
            )

        # Transactions
        transactions = (
            Transaction.query.filter_by(user_id=user_id)
            .order_by(Transaction.date_heure_transaction.desc())
            .limit(limit)
            .all()
        )
        for trans in transactions:
            montant = float(trans.montant) if trans.montant is not None else 0.0
            activity.append(
                {
                    "type": "transaction",
                    "timestamp": _iso(trans.date_heure_transaction),
                    "title": trans.libelle or "Transaction",
                    "details": f"{montant:.2f} {trans.devise or 'EUR'}",
                    "transaction_type": TransactionType.get_display_name(
                        trans.type_transaction
                    ),
                    "date_display": _format_dt(trans.date_heure_transaction),
                }
            )

        # Notifications
        notifications = (
            Notification.query.filter_by(user_id=user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .all()
        )
        for notif in notifications:
            activity.append(
                {
                    "type": "notification",
                    "timestamp": _iso(notif.created_at),
                    "title": notif.title,
                    "details": notif.message,
                    "is_read": bool(notif.is_read),
                    "date_display": _format_dt(notif.created_at),
                }
            )

        # Tri sur strings ISO (évite le piège datetime naive vs aware)
        activity.sort(key=lambda item: item["timestamp"], reverse=True)
        return activity[:limit]

    @staticmethod
    def get_user_accounts(user_id: int) -> Optional[List[Dict]]:
        """Récupère les comptes d'un utilisateur (données minimisées pour l'admin).

        N'expose PAS iban, bic_swift, account_number ni notes.
        Retourne None si l'utilisateur n'existe pas.
        """
        user = db.session.get(User, user_id)
        if not user:
            return None

        accounts = (
            Account.query.filter_by(user_id=user_id)
            .order_by(Account._is_active_db.desc(), Account.name)
            .all()
        )
        return [
            {
                "id": account.id,
                "name": account.name,
                "account_type": account.account_type,
                "balance": (
                    float(account.balance) if account.balance is not None else 0.0
                ),
                "currency": account.currency,
                "is_active": account.is_active,
                "is_primary": account.is_primary,
                "created_at": _format_dt(account.created_at, with_time=False),
            }
            for account in accounts
        ]

    @staticmethod
    def get_user_transactions(
        user_id: int, page: int = 1, per_page: int = 20
    ) -> Optional[Tuple[List[Dict], int]]:
        """Récupère les transactions paginées d'un utilisateur.

        Retourne (items, total) ou None si l'utilisateur n'existe pas.
        """
        user = db.session.get(User, user_id)
        if not user:
            return None

        query = (
            db.session.query(Transaction, Account.name)
            .outerjoin(Account, Transaction.account_id == Account.id)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.date_heure_transaction.desc())
        )
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()

        items = []
        for trans, account_name in rows:
            items.append(
                {
                    "id": trans.id,
                    "date": _format_dt(trans.date_heure_transaction),
                    "libelle": trans.libelle,
                    "montant": (
                        float(trans.montant) if trans.montant is not None else 0.0
                    ),
                    "type": trans.type_transaction,
                    "type_display": TransactionType.get_display_name(
                        trans.type_transaction
                    ),
                    "devise": trans.devise or "EUR",
                    "statut": trans.statut,
                    "account_name": account_name,
                }
            )
        return items, total

    @staticmethod
    def toggle_user_status(user_id: int) -> Tuple[bool, str]:
        """Active ou désactive un utilisateur"""
        user = db.session.get(User, user_id)
        if not user:
            return False, "Utilisateur non trouvé"

        user.is_active = not user.is_active
        db.session.commit()
        return True, f"Statut de l'utilisateur {user.username} mis à jour"

    @staticmethod
    def reset_user_2fa(user_id: int) -> Tuple[bool, str, Optional[str]]:
        """Réinitialise la 2FA pour un utilisateur"""
        user = db.session.get(User, user_id)
        if not user:
            return False, "Utilisateur non trouvé", None

        secret = generate_2fa_secret()
        user.two_factor_secret = secret
        user.two_factor_enabled = False  # Désactiver jusqu'à reconfiguration
        db.session.commit()

        return True, "2FA réinitialisée avec succès", secret

    @staticmethod
    def reset_user_password(user_id: int) -> Tuple[bool, str, Optional[str]]:
        """Réinitialise le mot de passe d'un utilisateur"""
        import string

        user = db.session.get(User, user_id)
        if not user:
            return False, "Utilisateur non trouvé", None

        # Générer un mot de passe temporaire sécurisé
        # secrets (et non random, non cryptographique) : mot de passe imprévisible
        import secrets

        characters = string.ascii_letters + string.digits + "!@#$%&*"
        new_password = "".join(secrets.choice(characters) for _ in range(16))

        # Le setter horodate le changement : sessions et jetons de l'utilisateur coupés
        user.password = new_password

        # Réinitialiser les tentatives de connexion si l'utilisateur était verrouillé
        user.login_attempts = 0
        user.is_locked = False

        db.session.commit()

        current_app.logger.info(
            f"Mot de passe réinitialisé pour l'utilisateur {user.username} (ID: {user_id})"
        )

        return (
            True,
            f"Mot de passe réinitialisé avec succès pour {user.username}",
            new_password,
        )

    @staticmethod
    def get_suspicious_transactions(limit: int = 20) -> List[Dict]:
        """Récupère les transactions suspectes (montants élevés, fréquence)"""
        try:
            # Transactions avec montants élevés (> 5000€)
            high_amount_transactions = db.session.execute(
                text("""
                    SELECT t.id, t.montant, t.libelle, t.date_heure_transaction,
                           u.username, a.nom_banque
                    FROM transactions t
                    JOIN users u ON t.user_id = u.id
                    JOIN "ComptesBancaires" a ON t.account_id = a.id_compte
                    WHERE ABS(t.montant) > 5000
                    ORDER BY t.date_heure_transaction DESC
                    LIMIT :limit
                """),
                {"limit": limit},
            ).fetchall()

            suspicious = []
            for row in high_amount_transactions:
                date_str = _format_dt(row.date_heure_transaction)

                suspicious.append(
                    {
                        "id": row.id,
                        "amount": float(row.montant),
                        "description": row.libelle,
                        "date": date_str,
                        "user": row.username,
                        "account": row.nom_banque,
                        "reason": f"Montant élevé: {abs(float(row.montant)):.2f}€",
                    }
                )

            return suspicious

        except Exception as e:
            current_app.logger.error(
                f"Erreur lors de la recherche de transactions suspectes: {e}"
            )
            return []

    @staticmethod
    def get_financial_summary() -> Dict:
        """Récupère un résumé financier global"""
        try:
            # Solde total de tous les comptes
            total_balance_result = db.session.execute(
                text(
                    'SELECT COALESCE(SUM(solde_actuel), 0) FROM "ComptesBancaires" WHERE est_actif = true'
                )
            ).scalar()
            total_balance = float(total_balance_result) if total_balance_result else 0.0

            # Revenus du mois
            month_start = datetime.now().replace(day=1).date()
            month_income_result = db.session.execute(
                text("""
                    SELECT COALESCE(SUM(montant), 0) FROM transactions 
                    WHERE montant > 0 AND date_heure_transaction >= :month_start
                """),
                {"month_start": month_start},
            ).scalar()
            month_income = float(month_income_result) if month_income_result else 0.0

            # Dépenses du mois
            month_expenses_result = db.session.execute(
                text("""
                    SELECT COALESCE(SUM(ABS(montant)), 0) FROM transactions 
                    WHERE montant < 0 AND date_heure_transaction >= :month_start
                """),
                {"month_start": month_start},
            ).scalar()
            month_expenses = (
                float(month_expenses_result) if month_expenses_result else 0.0
            )

            # Nombre de comptes avec solde négatif
            negative_accounts_result = db.session.execute(
                text(
                    'SELECT COUNT(*) FROM "ComptesBancaires" WHERE solde_actuel < 0 AND est_actif = true'
                )
            ).scalar()
            negative_accounts = (
                int(negative_accounts_result) if negative_accounts_result else 0
            )

            return {
                "total_balance": total_balance,
                "month_income": month_income,
                "month_expenses": month_expenses,
                "negative_accounts": negative_accounts,
            }

        except Exception as e:
            current_app.logger.error(f"Erreur lors du calcul du résumé financier: {e}")
            return {
                "total_balance": 0.0,
                "month_income": 0.0,
                "month_expenses": 0.0,
                "negative_accounts": 0,
            }
