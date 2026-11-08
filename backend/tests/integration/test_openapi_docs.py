"""Tests de la documentation OpenAPI / Swagger UI (api/v1/openapi.py)."""

import pytest


@pytest.mark.integration
def test_openapi_requires_auth(client):
    """La spec n'est pas exposee sans authentification."""
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code in (301, 302, 401)


@pytest.mark.integration
def test_openapi_spec_structure(auth_client):
    """La spec generee est un OpenAPI 3.0 valide et non vide."""
    resp = auth_client.get("/api/v1/openapi.json")
    assert resp.status_code == 200

    spec = resp.get_json()
    assert spec["openapi"] == "3.0.3"
    assert spec["paths"], "au moins une route doit etre documentee"

    # Les routes de documentation elles-memes sont exclues du catalogue
    assert "/api/v1/docs" not in spec["paths"]
    assert "/api/v1/openapi.json" not in spec["paths"]

    # Chaque operation porte un resume et un tag
    first_path = next(iter(spec["paths"].values()))
    first_op = next(iter(first_path.values()))
    assert "summary" in first_op
    assert first_op["tags"]

    # Schemas de securite declares
    schemes = spec["components"]["securitySchemes"]
    assert "sessionAuth" in schemes
    assert "bearerAuth" in schemes


@pytest.mark.integration
def test_openapi_path_params_converted(auth_client):
    """Les parametres Flask <id> sont convertis en {id} OpenAPI."""
    spec = auth_client.get("/api/v1/openapi.json").get_json()
    param_paths = [p for p in spec["paths"] if "{" in p]
    assert param_paths, "au moins une route a parametre attendue"
    # aucun reste de syntaxe Flask
    assert not any("<" in p for p in spec["paths"])


@pytest.mark.integration
def test_swagger_ui_page(auth_client):
    """La page Swagger UI se rend et pointe vers la spec."""
    resp = auth_client.get("/api/v1/docs")
    assert resp.status_code == 200

    html = resp.get_data(as_text=True)
    assert "swagger-ui" in html
    assert "cdn.jsdelivr.net" in html
    assert "/api/v1/openapi.json" in html
