"""
Modèles spécifiques pour l'import/export de données.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class FileFormat(str, Enum):
    """Formats de fichiers supportés pour l'import/export."""

    CSV = "csv"
    JSON = "json"
    EXCEL = "xlsx"


class ImportResult(BaseModel):
    """Résultat d'une opération d'import."""

    total_rows: int
    imported_rows: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    skipped: int = 0

    @property
    def success(self) -> bool:
        """Indique si l'import s'est déroulé sans erreur."""
        return len(self.errors) == 0 and self.imported_rows > 0


class ExportConfig(BaseModel):
    """Configuration pour l'export de données."""

    format: FileFormat = FileFormat.CSV
    include_transactions: bool = True
    include_accounts: bool = False
    include_categories: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    account_ids: List[int] = Field(default_factory=list)
    category_ids: List[int] = Field(default_factory=list)

    @field_validator("end_date")
    def validate_dates(cls, v, info: ValidationInfo):
        """Valide que la date de fin est postérieure à la date de début."""
        start_date = info.data.get("start_date")
        if start_date and v:
            if v < start_date:
                raise ValueError(
                    "La date de fin doit être postérieure à la date de début"
                )
        return v


class ImportConfig(BaseModel):
    """Configuration pour l'import de données."""

    format: FileFormat = FileFormat.CSV
    create_missing: bool = True
    update_existing: bool = False
    dry_run: bool = False
    max_errors: int = 100
    date_format: str = "%Y-%m-%d"
    decimal_separator: str = "."
    field_mapping: Dict[str, str] = Field(default_factory=dict)

    @field_validator("max_errors")
    def validate_max_errors(cls, v):
        """Valide le nombre maximum d'erreurs."""
        if v < 1:
            raise ValueError("Le nombre maximum d'erreurs doit être supérieur à 0")
        return v
