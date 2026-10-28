"""
Fichier centralisé pour les imports de l'application.
Permet de gérer les chemins d'import de manière centralisée.
"""

# Core
CORE_MODELS = "core.models"
CORE_SERVICES = "backend.core.services"

# Shared
SHARED_FORMS = "backend.shared.forms"
SHARED_UTILS = "backend.shared.utils"
SHARED_EXCEPTIONS = "backend.shared.exceptions"

# Modules
MODULES_AUTH = "backend.modules.auth"
MODULES_API = "backend.modules.api"
MODULES_MAIN = "backend.modules.main"

# Commands
COMMANDS = "backend.commands"


# Utilitaires
def import_from(module_path, class_name):
    """Importe dynamiquement une classe depuis un module."""
    module = __import__(module_path, fromlist=[class_name])
    return getattr(module, class_name)
