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

from core.services.profile import ProfileService

from .profile_forms import ChangePasswordForm, ProfileForm
from .profile_routes import profile_bp

__all__ = ["profile_bp", "ProfileForm", "ChangePasswordForm", "ProfileService"]
