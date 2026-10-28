"""
API REST v1 — Documentation OpenAPI (catalogue auto-genere) + Swagger UI.

La specification est construite automatiquement par introspection de la table
de routage Flask : chaque route sous /api/v1/ devient une operation, avec son
chemin, ses methodes, ses parametres de chemin et un resume tire de la
docstring de la vue. Les schemas detailles requete/reponse ne sont pas inclus
(catalogue), mais la spec reste enrichissable route par route ensuite.

Routes:
    GET /api/v1/openapi.json   Specification OpenAPI 3.0 generee depuis les routes
    GET /api/v1/docs           Interface Swagger UI
"""

import re

from flask import current_app, g, jsonify, render_template_string
from flask_login import login_required

from . import api_v1_bp

# Swagger UI servi depuis jsDelivr, deja autorise par la CSP de l'application
# (script-src / style-src incluent https://cdn.jsdelivr.net).
SWAGGER_UI_VERSION = "5.17.14"

# Routes de documentation elles-memes, exclues du catalogue.
_DOC_ROUTES = {"/api/v1/openapi.json", "/api/v1/docs"}

# <int:id> ou <id> -> {id}
_PATH_PARAM_RE = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")


def _build_openapi_spec():
    """Construit la specification OpenAPI 3.0 depuis la table de routage."""
    paths = {}
    tags = set()

    for rule in current_app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v1/") or rule.rule in _DOC_ROUTES:
            continue

        openapi_path = _PATH_PARAM_RE.sub(r"{\1}", rule.rule)
        view = current_app.view_functions.get(rule.endpoint)
        doc = (view.__doc__ or "").strip() if view else ""
        summary = doc.splitlines()[0].strip() if doc else rule.endpoint

        # Tag = nom du module de la vue (api.v1.accounts -> accounts)
        module = getattr(view, "__module__", "") if view else ""
        tag = module.rsplit(".", 1)[-1] if module else "api"
        tags.add(tag)

        parameters = [
            {
                "name": arg,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
            for arg in sorted(rule.arguments)
        ]

        path_item = paths.setdefault(openapi_path, {})
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            operation = {
                "summary": summary,
                "tags": [tag],
                "responses": {
                    "200": {"description": "Succes"},
                    "401": {"description": "Authentification requise"},
                },
            }
            if parameters:
                operation["parameters"] = parameters
            path_item[method.lower()] = operation

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "API Budget — v1",
            "version": "1.0.0",
            "description": (
                "Catalogue auto-genere des routes de l'API REST v1. "
                "Les resumes proviennent des docstrings des vues ; les schemas "
                "detailles requete/reponse ne sont pas (encore) documentes."
            ),
        },
        "tags": [{"name": t} for t in sorted(tags)],
        "components": {
            "securitySchemes": {
                "sessionAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session",
                },
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                },
            }
        },
        # La plupart des routes acceptent la session (web) ou un JWT (API).
        "security": [{"sessionAuth": []}, {"bearerAuth": []}],
        "paths": paths,
    }


@api_v1_bp.route("/openapi.json", methods=["GET"])
@login_required
def openapi_spec():
    """Specification OpenAPI 3.0 generee automatiquement depuis les routes."""
    return jsonify(_build_openapi_spec())


_SWAGGER_UI_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>API Budget — Documentation</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{{ version }}/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{{ version }}/swagger-ui-bundle.js"
          nonce="{{ nonce }}"></script>
  <script nonce="{{ nonce }}">
    window.ui = SwaggerUIBundle({
      url: "/api/v1/openapi.json",
      dom_id: "#swagger-ui",
      deepLinking: true,
      presets: [SwaggerUIBundle.presets.apis]
    });
  </script>
</body>
</html>"""


@api_v1_bp.route("/docs", methods=["GET"])
@login_required
def swagger_ui():
    """Interface Swagger UI pour explorer l'API."""
    return render_template_string(
        _SWAGGER_UI_TEMPLATE,
        nonce=getattr(g, "csp_nonce", ""),
        version=SWAGGER_UI_VERSION,
    )
