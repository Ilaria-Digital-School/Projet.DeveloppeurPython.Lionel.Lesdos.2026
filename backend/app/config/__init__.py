"""
Configuration de l'application.
"""

from .config import Config, DevelopmentConfig, ProductionConfig, TestingConfig, config
from .database import db, migrate

__all__ = [
    "db",
    "migrate",
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "ProductionConfig",
    "config",
]
