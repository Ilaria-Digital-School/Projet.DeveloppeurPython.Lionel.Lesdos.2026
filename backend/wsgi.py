"""
Point d'entrée WSGI pour le déploiement en production.
Ce module permet de servir l'application via un serveur WSGI comme Gunicorn ou uWSGI.
"""

import os
import sys

from dotenv import load_dotenv
from flask_moment import Moment

# Charger les variables d'environnement
load_dotenv()

# Ajouter le répertoire backend au chemin Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


def create_app():
    """Crée et configure une instance de l'application Flask."""
    from app import create_app as create_flask_app

    # Créer l'application avec la configuration appropriée
    app = create_flask_app()

    # Initialiser Flask-Moment
    Moment(app)

    # Configuration pour le serveur WSGI (en production)
    # Ne pas forcer le mode DEBUG ici pour éviter les conflits avec la configuration de développement
    app.config.update(
        PREFERRED_URL_SCHEME="https",
        # Ne propager les exceptions que si le mode debug est actif
        PROPAGATE_EXCEPTIONS=app.debug,
    )

    # Configurer le logging
    import logging

    log_level = logging.DEBUG if app.debug else logging.INFO
    log_dir = os.path.join(current_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=os.path.join(log_dir, "wsgi.log"),
        filemode="a",
    )

    # Afficher les chemins de recherche des templates
    app.logger.info(f"Template folder: {app.template_folder}")
    app.logger.info(f"Static folder: {app.static_folder}")

    # Vérifier si le dossier des templates existe
    if not os.path.exists(app.template_folder):
        app.logger.error(
            f"Le dossier des templates n'existe pas: {app.template_folder}"
        )
    else:
        app.logger.info(
            f"Contenu du dossier des templates: {os.listdir(app.template_folder)}"
        )

    return app


# Créer l'application pour le serveur WSGI
application = create_app()

if __name__ == "__main__":
    # Exécuter l'application en mode développement
    port = int(os.getenv("PORT", 5000))
    application.run(
        host="0.0.0.0",  # nosec B104 - bind toutes interfaces voulu (dev en conteneur)
        port=port,
        debug=os.getenv("FLASK_ENV") == "development",
    )
