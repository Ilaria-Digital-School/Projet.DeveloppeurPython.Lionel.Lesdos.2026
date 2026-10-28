"""
Module d'administration
Fournit des fonctionnalités d'administration du système via API REST
"""

import logging

logger = logging.getLogger(__name__)


# Blueprint pour les routes d'API
def create_blueprint():
    """Crée et retourne le blueprint pour les routes d'API"""
    from . import routes

    return routes.bp


def init_app(app):
    """Initialise le module d'administration avec les routes API seulement"""
    try:
        # Enregistrement des routes d'API
        from . import routes

        app.register_blueprint(routes.bp)
        logger.info("Module d'administration API initialisé avec succès")

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'administration: {str(e)}")
        raise
