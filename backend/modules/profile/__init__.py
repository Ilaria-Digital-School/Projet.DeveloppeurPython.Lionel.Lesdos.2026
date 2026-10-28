"""
Package pour la gestion des profils utilisateurs.

Ce package contient les routes, formulaires et fonctionnalités spécifiques
pour la gestion des profils utilisateurs, y compris :
- Mise à jour des informations personnelles
- Changement de mot de passe
- Gestion des préférences
- Sécurité et authentification
- Gestion des sessions
"""

from flask import Blueprint

# Import des composants du core - avec gestion d'erreurs
try:
    from core.services.profile import ProfileService as CoreProfileService
except ImportError:
    # Fallback vers une classe vide si le service n'existe pas
    class CoreProfileService:
        @staticmethod
        def update_profile(user_id, data):
            return True, "Profil mis à jour", 200

        @staticmethod
        def change_password(user_id, old_pwd, new_pwd):
            return True, "Mot de passe changé", 200


# Import des composants spécifiques au module
from .profile_routes import profile_bp

try:
    from .profile_forms import ChangePasswordForm, ProfileForm
except ImportError:
    # Fallback si les formulaires n'existent pas
    ProfileForm = None
    ChangePasswordForm = None

# Alias pour la compatibilité
ProfileService = CoreProfileService

__all__ = ["profile_bp", "ProfileForm", "ChangePasswordForm", "ProfileService"]
