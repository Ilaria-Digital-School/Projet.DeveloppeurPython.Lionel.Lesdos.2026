"""Configuration de sécurité pour le service d'authentification."""

from datetime import timedelta

# Complexité des mots de passe
PASSWORD_COMPLEXITY = {
    "min_length": 12,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special_char": True,
    "special_chars": "!@#$%^&*()_+-=[]{}|;:,.<>?",
}

# Tentatives de connexion
LOGIN_ATTEMPTS_LIMIT = 5
LOGIN_LOCKOUT_TIME = timedelta(minutes=15)

# Messages d'erreur
ERROR_MESSAGES = {
    "account_locked": "Votre compte est temporairement verrouillé. Veuillez réessayer plus tard ou réinitialiser votre mot de passe.",
    "invalid_credentials": "Nom d'utilisateur ou mot de passe incorrect",
    "password_too_weak": "Le mot de passe ne respecte pas les exigences de sécurité",
    "password_mismatch": "Les mots de passe ne correspondent pas",
    "user_not_found": "Aucun utilisateur trouvé avec cet identifiant",
    "email_already_used": "Cette adresse email est déjà utilisée",
    "username_already_used": "Ce nom d'utilisateur est déjà pris",
    "invalid_token": "Le jeton fourni est invalide ou a expiré",
    "permission_denied": "Vous n'avez pas les permissions nécessaires pour effectuer cette action",
    "validation_error": "Erreur de validation des données",
    "rate_limit_exceeded": "Trop de tentatives. Veuillez réessayer plus tard.",
}
