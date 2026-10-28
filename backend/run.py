"""
Point d'entree pour le developpement local.

Ce script permet de lancer l'application en mode developpement avec la configuration appropriee.
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Configuration du logging (avant la creation de l'app Flask)
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Definir les chemins importants
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent  # Racine du projet

# Afficher les informations de debogage
logger.debug(f"Repertoire de travail: {os.getcwd()}")
logger.debug(f"Repertoire de base (backend): {BASE_DIR}")
logger.debug(f"Racine du projet: {PROJECT_ROOT}")
logger.debug(f"PYTHONPATH initial: {sys.path}")

# Ajouter les chemins necessaires au PYTHONPATH
paths_to_add = [str(PROJECT_ROOT), str(BASE_DIR)]  # Racine du projet  # Dossier backend

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)
        logger.debug(f"Ajout au PYTHONPATH: {path}")

# Afficher le PYTHONPATH mis a jour
logger.debug(f"Nouveau PYTHONPATH: {sys.path}")

# Charger les variables d'environnement
load_dotenv()

# Definir les variables d'environnement necessaires
os.environ["FLASK_APP"] = "app:create_app"  # Chemin relatif vers create_app
os.environ["FLASK_ENV"] = "development"

# Afficher les variables d'environnement pour le debogage
logger.debug(f"FLASK_APP: {os.environ.get('FLASK_APP')}")
logger.debug(f"FLASK_ENV: {os.environ.get('FLASK_ENV')}")

# Masquer les credentials de DATABASE_URL avant de logger
_db_url = os.environ.get("DATABASE_URL")
if _db_url:
    import re

    _db_url = re.sub(r"//([^:/@]+):[^@]+@", r"//\1:***@", _db_url)
logger.debug(f"DATABASE_URL: {_db_url}")

# Importer et creer l'application
try:
    logger.debug("Tentative d'import de l'application...")
    from app import create_app

    logger.debug("Import de l'application reussi!")
    app = create_app()
except ImportError as e:
    logger.error(f"Echec de l'import de l'application: {e}")
    logger.debug(f"Liste des modules disponibles: {list(sys.modules.keys())}")
    raise

if __name__ == "__main__":
    # Creer le repertoire des logs s'il n'existe pas
    logs_dir = os.path.join(BASE_DIR, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)
        logger.debug(f"Repertoire de logs cree: {logs_dir}")

    # Demarrer l'application en mode developpement
    port = int(os.environ.get("FLASK_PORT", 8080))
    logger.info(f"Demarrage de l'application sur http://0.0.0.0:{port}...")
    app.run(
        host="0.0.0.0",  # nosec B104 - bind toutes interfaces voulu (dev en conteneur)
        port=port,
        debug=True,
        use_reloader=True,
        use_debugger=True,
    )
