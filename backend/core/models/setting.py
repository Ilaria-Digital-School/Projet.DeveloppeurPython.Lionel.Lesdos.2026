"""
Modèles pour la gestion des paramètres utilisateur.
"""

from datetime import datetime, timezone
from enum import Enum

from ..extensions import db


class SettingType(Enum):
    """Types de paramètres utilisateur."""

    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    JSON = "json"
    DATETIME = "datetime"


class UserSetting(db.Model):
    """
    Modèle pour stocker les paramètres personnalisés des utilisateurs.
    """

    __tablename__ = "user_settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Text)
    setting_type = db.Column(
        db.Enum(SettingType, native_enum=False, length=20),
        nullable=False,
        default=SettingType.STRING,
    )
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relation avec l'utilisateur
    user = db.relationship("User", back_populates="settings")

    __table_args__ = (db.UniqueConstraint("user_id", "key", name="_user_setting_uc"),)

    def __repr__(self):
        return f"<UserSetting {self.user_id}:{self.key}={self.value}>"

    def get_value(self):
        """Retourne la valeur convertie dans le bon type."""
        if self.value is None:
            return None

        if self.setting_type == SettingType.BOOLEAN:
            return self.value.lower() in ("true", "1", "t", "y", "yes")
        elif self.setting_type == SettingType.INTEGER:
            return int(self.value)
        elif self.setting_type == SettingType.FLOAT:
            return float(self.value)
        elif self.setting_type == SettingType.JSON:
            import json

            return json.loads(self.value)
        elif self.setting_type == SettingType.DATETIME:
            from dateutil.parser import parse

            return parse(self.value)
        return self.value

    def set_value(self, value):
        """Définit la valeur avec conversion en chaîne si nécessaire."""
        import json
        from datetime import datetime

        if value is None:
            self.value = None
            self.setting_type = SettingType.STRING
        elif isinstance(value, bool):
            self.value = str(value).lower()
            self.setting_type = SettingType.BOOLEAN
        elif isinstance(value, int):
            self.value = str(value)
            self.setting_type = SettingType.INTEGER
        elif isinstance(value, float):
            self.value = str(value)
            self.setting_type = SettingType.FLOAT
        elif isinstance(value, (dict, list)):
            self.value = json.dumps(value, ensure_ascii=False)
            self.setting_type = SettingType.JSON
        elif isinstance(value, datetime):
            self.value = value.isoformat()
            self.setting_type = SettingType.DATETIME
        else:
            self.value = str(value)
            self.setting_type = SettingType.STRING

    @classmethod
    def get_setting(cls, user_id, key, default=None):
        """Récupère un paramètre utilisateur."""
        setting = cls.query.filter_by(user_id=user_id, key=key).first()
        if setting is None:
            return default
        return setting.get_value()

    @classmethod
    def set_setting(cls, user_id, key, value):
        """Définit un paramètre utilisateur."""
        setting = cls.query.filter_by(user_id=user_id, key=key).first()

        if setting is None:
            setting = cls(user_id=user_id, key=key)
            db.session.add(setting)

        setting.set_value(value)
        db.session.commit()
        return setting
