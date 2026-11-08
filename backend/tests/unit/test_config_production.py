"""Configuration de production : Redis exigé au démarrage, pas à l'import."""

import pytest
from flask import Flask

from app.config.config import configurer_redis_production


def test_refuse_sans_redis_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        configurer_redis_production(Flask(__name__))


def test_configure_la_connexion_des_sessions(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    app = Flask(__name__)
    configurer_redis_production(app)
    assert (
        app.config["SESSION_REDIS"].connection_pool.connection_kwargs["host"]
        == "localhost"
    )
