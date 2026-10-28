"""Tests du service de parametres utilisateur (SettingService)."""

import io
import json
import zipfile

import pytest

from core.services.settings.setting_services import SettingService


@pytest.mark.unit
class TestUserSettings:
    def test_set_and_get_roundtrip_preserve_types(self, user):
        """set_user_setting conserve les types (str, int, bool) au relecture."""
        SettingService.set_user_setting(user.id, "devise", "EUR")
        SettingService.set_user_setting(user.id, "page_size", 25)
        SettingService.set_user_setting(user.id, "notifications", True)

        settings = SettingService.get_user_settings(user.id)
        assert settings["devise"] == "EUR"
        assert settings["page_size"] == 25
        assert settings["notifications"] is True

    def test_set_updates_existing_key(self, user):
        """Redefinir une cle existante met a jour la valeur."""
        SettingService.set_user_setting(user.id, "devise", "EUR")
        SettingService.set_user_setting(user.id, "devise", "USD")

        settings = SettingService.get_user_settings(user.id, keys=["devise"])
        assert settings["devise"] == "USD"

    def test_get_with_keys_returns_none_for_missing(self, user):
        """get_user_settings(keys=...) renvoie None pour une cle absente."""
        result = SettingService.get_user_settings(user.id, keys=["inexistant"])
        assert result == {"inexistant": None}

    def test_get_all_empty_for_new_user(self, user):
        """Un utilisateur sans parametre renvoie un dict vide."""
        assert SettingService.get_user_settings(user.id) == {}

    def test_delete_existing_then_missing(self, user):
        """delete renvoie True si present, False sinon, et supprime bien."""
        SettingService.set_user_setting(user.id, "theme", "sombre")

        assert SettingService.delete_user_setting(user.id, "theme") is True
        assert SettingService.get_user_settings(user.id, keys=["theme"]) == {
            "theme": None
        }
        assert SettingService.delete_user_setting(user.id, "theme") is False


@pytest.mark.unit
class TestExportUserData:
    def test_export_json(self, user, account, category, transaction):
        """L'export JSON contient toutes les sections attendues."""
        output, filename, mimetype = SettingService.export_user_data(
            user.id, export_format="json"
        )
        assert filename.endswith(".json")
        assert mimetype == "application/json"

        payload = json.loads(output.getvalue().decode("utf-8"))
        assert payload["user"]["id"] == user.id
        for section in ("settings", "accounts", "categories", "transactions"):
            assert section in payload
        assert len(payload["accounts"]) >= 1
        assert len(payload["transactions"]) >= 1

    def test_export_csv_is_zip(self, user, account, category, transaction):
        """L'export CSV renvoie une archive ZIP contenant les fichiers."""
        output, filename, mimetype = SettingService.export_user_data(
            user.id, export_format="csv"
        )
        assert filename.endswith(".zip")
        assert mimetype == "application/zip"

        with zipfile.ZipFile(io.BytesIO(output.getvalue())) as zf:
            names = zf.namelist()
        assert "user.csv" in names
        assert "accounts.csv" in names
        assert "transactions.csv" in names

    def test_export_excel(self, user, account):
        """L'export Excel renvoie un .xlsx avec le bon type MIME."""
        output, filename, mimetype = SettingService.export_user_data(
            user.id, export_format="excel"
        )
        assert filename.endswith(".xlsx")
        assert "spreadsheetml" in mimetype
        # Signature ZIP d'un fichier xlsx
        assert output.getvalue()[:2] == b"PK"

    def test_export_unsupported_format_raises(self, user):
        """Un format inconnu leve ValueError."""
        with pytest.raises(ValueError):
            SettingService.export_user_data(user.id, export_format="xml")
