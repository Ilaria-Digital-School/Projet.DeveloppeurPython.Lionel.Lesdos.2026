"""Tests des validateurs du tableau de bord (modules/dashboard/dashboard_validators.py)."""

from datetime import date

import pytest
from wtforms import ValidationError

from modules.dashboard.dashboard_validators import (
    sanitize_search_query,
    validate_date_format,
    validate_date_range,
    validate_export_format,
    validate_limit,
)

pytestmark = pytest.mark.unit


class TestValidateDateFormat:
    def test_empty_returns_none(self):
        assert validate_date_format("") is None
        assert validate_date_format(None) is None

    def test_valid_date(self):
        assert validate_date_format("2024-01-15") == date(2024, 1, 15)

    def test_invalid_date_raises(self):
        with pytest.raises(ValidationError):
            validate_date_format("15/01/2024")


class TestValidateDateRange:
    def test_valid_range_ok(self):
        # Ne doit rien lever
        validate_date_range(date(2024, 1, 1), date(2024, 1, 31))

    def test_start_after_end_raises(self):
        with pytest.raises(ValidationError):
            validate_date_range(date(2024, 2, 1), date(2024, 1, 1))

    def test_missing_bound_ok(self):
        validate_date_range(None, date(2024, 1, 1))
        validate_date_range(date(2024, 1, 1), None)


class TestValidateExportFormat:
    @pytest.mark.parametrize("fmt", ["json", "JSON", "csv", "CSV"])
    def test_accepted_formats_lowercased(self, fmt):
        assert validate_export_format(fmt) == fmt.lower()

    def test_rejected_format_raises(self):
        with pytest.raises(ValidationError):
            validate_export_format("xml")


class TestValidateLimit:
    def test_valid_int_and_str(self):
        assert validate_limit(50) == 50
        assert validate_limit("50") == 50

    @pytest.mark.parametrize("bad", [0, 101, -5])
    def test_out_of_range_raises(self, bad):
        with pytest.raises(ValidationError):
            validate_limit(bad)

    @pytest.mark.parametrize("bad", ["abc", None])
    def test_non_integer_raises(self, bad):
        with pytest.raises(ValidationError):
            validate_limit(bad)

    def test_custom_max_limit(self):
        assert validate_limit(200, max_limit=500) == 200
        with pytest.raises(ValidationError):
            validate_limit(200, max_limit=100)


class TestSanitizeSearchQuery:
    def test_none_or_non_str_returns_empty(self):
        assert sanitize_search_query(None) == ""
        assert sanitize_search_query(123) == ""

    def test_removes_dangerous_chars(self):
        assert sanitize_search_query("hello<script>") == "helloscript"

    def test_keeps_word_space_hyphen(self):
        assert sanitize_search_query("  cafe-bar 2024 ") == "cafe-bar 2024"

    def test_truncates_to_100_chars(self):
        assert len(sanitize_search_query("a" * 200)) == 100
