from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy.orm import Mapped

# Imports absolus depuis le package racine
from core.extensions import db


class Account(db.Model):
    """
    Modèle représentant un compte bancaire.

    Un compte peut être de différents types (courant, épargne, etc.) et est associé à un utilisateur.
    Il contient des informations sur le solde, la devise et d'autres métadonnées.
    """

    __tablename__ = "ComptesBancaires"
    __table_args__ = (
        db.Index("idx_account_user", "utilisateur_id"),
        {"extend_existing": True},
    )

    # Colonnes principales
    id = db.Column("id_compte", db.Integer, primary_key=True)
    user_id = db.Column(
        "utilisateur_id",
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Informations du compte (colonnes de base de données)
    name: Mapped[str] = db.Column("nom_banque", db.String(100), nullable=False)
    _account_type_db: Mapped[str] = db.Column(
        "type_compte", db.String(50), nullable=False, default="courant"
    )
    _balance_db: Mapped[Decimal] = db.Column(
        "solde_actuel", db.Numeric(12, 2), default=0.0, nullable=False
    )
    # Solde de départ : solde_actuel doit toujours valoir solde_initial + effet
    # des transactions (cf. core/services/accounts/balance_check.py)
    _initial_balance_db: Mapped[Decimal] = db.Column(
        "solde_initial",
        db.Numeric(12, 2),
        default=0,
        server_default="0",
        nullable=False,
    )
    _currency_db: Mapped[str] = db.Column(
        "devise", db.String(3), default="EUR", nullable=False
    )

    # Pour éviter les erreurs avec les annotations de type non reconnues
    __allow_unmapped__ = True

    # Informations bancaires
    bank_name = db.Column("nom_banque_detail", db.String(100), nullable=True)
    account_number = db.Column("numero_compte", db.String(50), nullable=True)
    iban = db.Column("iban", db.String(34), unique=True, nullable=True)
    bic_swift = db.Column("bic_swift", db.String(11), nullable=True)

    # Métadonnées
    _is_active_db = db.Column("est_actif", db.Boolean, default=True, nullable=False)
    _is_primary_db = db.Column(
        "est_compte_principal", db.Boolean, default=False, nullable=False
    )
    notes = db.Column("notes", db.Text, nullable=True)

    # Dates
    created_at = db.Column(
        "date_ouverture",
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        "date_mise_a_jour",
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # La relation avec les transactions est gérée par les backrefs dans le modèle Transaction
    # pour éviter les conflits de relations circulaires

    # Attributs privés pour éviter la récursion
    _account_type: str
    _currency: str
    _is_active: bool
    _is_primary: bool

    # Propriétés de compatibilité
    @property
    def utilisateur_id(self) -> int:
        """Alias pour user_id (compatibilité)"""
        return self.user_id

    @utilisateur_id.setter
    def utilisateur_id(self, value: int) -> None:
        self.user_id = value

    @property
    def nom_banque(self) -> str:
        """Alias pour name (compatibilité)"""
        return self.name

    @nom_banque.setter
    def nom_banque(self, value: str) -> None:
        self.name = value

    @property
    def type_compte(self) -> str:
        """Alias pour account_type (compatibilité)"""
        return self._account_type

    @type_compte.setter
    def type_compte(self, value: str) -> None:
        self._account_type = value

    @property
    def account_type(self) -> str:
        """Type de compte (courant, épargne, etc.)"""
        if not hasattr(self, "_account_type") or self._account_type is None:
            if hasattr(self, "_account_type_db") and self._account_type_db is not None:
                self._account_type = str(self._account_type_db)
            else:
                self._account_type = "courant"
        return self._account_type

    @account_type.setter
    def account_type(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("Le type de compte doit être une chaîne de caractères")
        self._account_type = value
        # Mise à jour de la colonne de base de données si elle existe
        if hasattr(self, "_account_type_db"):
            self._account_type_db = value

    @property
    def solde_actuel(self) -> Decimal:
        """Alias pour balance (compatibilité)"""
        return self.balance

    @solde_actuel.setter
    def solde_actuel(self, value) -> None:
        if isinstance(value, (int, float)):
            self.balance = Decimal(str(value))
        elif isinstance(value, Decimal):
            self.balance = value
        else:
            raise ValueError("Le solde doit être un nombre")

    @property
    def balance(self) -> Decimal:
        """Solde actuel du compte.

        Lu directement depuis la colonne (pas de copie en cache) : les
        transactions mettent solde_actuel à jour en SQL brut, et une copie
        privée restait périmée après db.session.expire_all().
        """
        if self._balance_db is None:
            return Decimal("0.00")
        return Decimal(str(self._balance_db))

    @balance.setter
    def balance(self, value) -> None:
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif value is None:
            value = Decimal("0.00")
        elif not isinstance(value, Decimal):
            raise ValueError("Le solde doit être un nombre")
        self._balance_db = value

    @property
    def initial_balance(self) -> Decimal:
        """Solde de départ du compte (avant toute transaction)."""
        if self._initial_balance_db is None:
            return Decimal("0.00")
        return Decimal(str(self._initial_balance_db))

    @initial_balance.setter
    def initial_balance(self, value) -> None:
        self._initial_balance_db = Decimal(str(value))

    def ajuster_solde(self, nouveau_solde) -> None:
        """Saisie manuelle du solde : décale aussi le solde initial du même écart,
        pour que solde_actuel = solde_initial + transactions reste vrai."""
        ecart = Decimal(str(nouveau_solde)) - self.balance
        self.balance = Decimal(str(nouveau_solde))
        self.initial_balance = self.initial_balance + ecart

    @property
    def solde_disponible(self) -> Decimal:
        """Solde disponible (égal au solde actuel)"""
        return self.balance

    @solde_disponible.setter
    def solde_disponible(self, value) -> None:
        if not isinstance(value, (int, float, Decimal)):
            raise ValueError("Le solde disponible doit être un nombre")
        self.balance = value

    @property
    def devise(self) -> str:
        """Alias pour currency (compatibilité)"""
        return self.currency

    @devise.setter
    def devise(self, value: str) -> None:
        if value and len(value) == 3 and value.isalpha():
            self.currency = value.upper()
        else:
            raise ValueError("La devise doit être un code à 3 lettres")

    @property
    def currency(self) -> str:
        """Devise du compte (code ISO 4217, 3 lettres)"""
        if not hasattr(self, "_currency") or self._currency is None:
            if hasattr(self, "_currency_db") and self._currency_db is not None:
                self._currency = str(self._currency_db).upper()
            else:
                self._currency = "EUR"
        return self._currency

    @currency.setter
    def currency(self, value: str) -> None:
        if not value:
            value = "EUR"
        if not (isinstance(value, str) and len(value) == 3 and value.isalpha()):
            raise ValueError("La devise doit être un code à 3 lettres (ex: EUR, USD)")

        self._currency = value.upper()
        # Mise à jour de la colonne de base de données si elle existe
        if hasattr(self, "_currency_db"):
            self._currency_db = self._currency

    @property
    def est_actif(self) -> bool:
        """Alias pour is_active (compatibilité)"""
        return self.is_active

    @est_actif.setter
    def est_actif(self, value: bool) -> None:
        self.is_active = bool(value)

    @property
    def is_active(self) -> bool:
        """Indique si le compte est actif"""
        if not hasattr(self, "_is_active") or self._is_active is None:
            if hasattr(self, "_is_active_db") and self._is_active_db is not None:
                self._is_active = bool(self._is_active_db)
            else:
                self._is_active = True
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._is_active = bool(value)
        # Mise à jour de la colonne de base de données si elle existe
        if hasattr(self, "_is_active_db"):
            self._is_active_db = self._is_active

    @property
    def est_compte_principal(self) -> bool:
        """Alias pour is_primary (compatibilité)"""
        return self.is_primary

    @est_compte_principal.setter
    def est_compte_principal(self, value: bool) -> None:
        self.is_primary = bool(value)

    @property
    def is_primary(self) -> bool:
        """Indique si c'est le compte principal de l'utilisateur"""
        if not hasattr(self, "_is_primary") or self._is_primary is None:
            if hasattr(self, "_is_primary_db") and self._is_primary_db is not None:
                self._is_primary = bool(self._is_primary_db)
            else:
                self._is_primary = False
        return self._is_primary

    @is_primary.setter
    def is_primary(self, value: bool) -> None:
        self._is_primary = bool(value)
        # Mise à jour de la colonne de base de données si elle existe
        if hasattr(self, "_is_primary_db"):
            self._is_primary_db = self._is_primary

    @property
    def available_balance(self) -> Decimal:
        """Alias pour solde_disponible (compatibilité anglaise)"""
        return self.solde_disponible

    @available_balance.setter
    def available_balance(self, value) -> None:
        self.solde_disponible = value

    def __init__(self, **kwargs):
        # Récupération des valeurs avant l'appel au constructeur parent
        account_type = kwargs.pop("account_type", "courant")
        balance = kwargs.pop("balance", Decimal("0.00"))
        initial_balance = kwargs.pop("initial_balance", None)
        currency = kwargs.pop("currency", "EUR")
        is_active = kwargs.pop("is_active", True)
        is_primary = kwargs.pop("is_primary", False)

        # Initialisation des colonnes de base de données directement (utiliser les noms d'attributs internes)
        kwargs["_account_type_db"] = account_type
        kwargs["_balance_db"] = (
            balance if isinstance(balance, Decimal) else Decimal(str(balance))
        )
        # Un nouveau compte part de son solde d'ouverture
        kwargs["_initial_balance_db"] = Decimal(
            str(initial_balance if initial_balance is not None else balance)
        )
        kwargs["_currency_db"] = currency
        kwargs["_is_active_db"] = is_active
        kwargs["_is_primary_db"] = is_primary

        # Appel au constructeur parent
        super(Account, self).__init__(**kwargs)

        # Initialisation des attributs privés pour cohérence
        self._account_type = account_type
        self._currency = currency
        self._is_active = is_active
        self._is_primary = is_primary

    def __repr__(self) -> str:
        return f"<Account {self.id}: {self.name} ({self.account_type})>"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le compte en dictionnaire pour la sérialisation JSON.

        Returns:
            Dict[str, Any]: Dictionnaire représentant le compte
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "account_type": self.account_type,
            "balance": float(self.balance) if self.balance is not None else 0.0,
            "currency": self.currency,
            "iban": self.iban,
            "bic_swift": self.bic_swift,
            "is_active": self.is_active,
            "is_primary": self.is_primary,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
