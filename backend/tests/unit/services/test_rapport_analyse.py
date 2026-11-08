"""Tests de la période de comparaison des rapports détaillés."""

from datetime import date

import pytest

from core.services.reports.analyse import periode_precedente


@pytest.mark.parametrize(
    "debut, fin, date_range, attendu",
    [
        # Mois en cours : mêmes jours du mois précédent
        (
            date(2026, 11, 1),
            date(2026, 11, 5),
            "current_month",
            ("2026-10-01", "2026-10-05"),
        ),
        # Mois complet de 31 jours -> mois précédent complet (février)
        (
            date(2026, 3, 1),
            date(2026, 3, 31),
            "last_month",
            ("2026-02-01", "2026-02-28"),
        ),
        # Année en cours : même partie de l'année précédente
        (
            date(2026, 1, 1),
            date(2026, 11, 5),
            "current_year",
            ("2025-01-01", "2025-11-05"),
        ),
        (
            date(2025, 1, 1),
            date(2025, 12, 31),
            "last_year",
            ("2024-01-01", "2024-12-31"),
        ),
        # Période personnalisée : même nombre de jours juste avant
        (date(2026, 6, 11), date(2026, 6, 20), "custom", ("2026-06-01", "2026-06-10")),
    ],
)
def test_periode_precedente(debut, fin, date_range, attendu):
    prec = periode_precedente(debut, fin, date_range)
    assert tuple(d.isoformat() for d in prec) == attendu


@pytest.mark.parametrize(
    "libelle, attendu",
    [
        ("CB SUPERMARCHE FR0001 FACT 010126", "SUPERMARCHE"),
        ("PRLV Free Telecom", "FREE TELECOM"),
        ("PRLV ASSUREUR 12345 VILLE CEDEX", "ASSUREUR"),
        ("PAYPAL · NETFLIX", "NETFLIX"),
        ("VIR SEPA JEAN DUPONT", "JEAN DUPONT"),
        ("VIR INST JEAN MARTIN", "JEAN MARTIN"),
        ("CB E.LECLERC FACT 230326", "E.LECLERC"),
        ("Loyer", "LOYER"),
        ("", "SANS LIBELLÉ"),
    ],
)
def test_nom_destinataire(libelle, attendu):
    from core.services.reports.analyse import nom_destinataire

    assert nom_destinataire(libelle) == attendu


def test_resolution_des_nouvelles_periodes(monkeypatch):
    """Bornes des périodes ajoutées, à une date fixe (5 novembre 2026)."""
    import datetime as dt

    import api.v1.reports as reports

    class FauxDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 5, 12, 0)

    monkeypatch.setattr(reports, "datetime", FauxDatetime)
    attendu = {
        "last_3_months": ("2026-09-01", "2026-11-05"),
        "last_6_months": ("2026-06-01", "2026-11-05"),
        "last_12_months": ("2025-12-01", "2026-11-05"),
        "current_quarter": ("2026-10-01", "2026-11-05"),
        "last_quarter": ("2026-07-01", "2026-09-30"),
    }
    for date_range, (debut, fin) in attendu.items():
        bornes = reports._resolve_date_range(date_range, {})
        assert tuple(d.isoformat() for d in bornes) == (debut, fin), date_range


def test_periode_precedente_des_trimestres():
    prec = periode_precedente(date(2026, 7, 1), date(2026, 9, 30), "last_quarter")
    assert tuple(d.isoformat() for d in prec) == ("2026-04-01", "2026-06-30")
