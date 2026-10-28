"""
Classes d'exception personnalisées pour l'application.

Ce module contient les classes d'exception utilisées dans les services
et modules de l'application pour une gestion d'erreur cohérente.
"""


class ValidationError(Exception):
    """Exception levée lors d'erreurs de validation des données."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class NotFoundError(Exception):
    """Exception levée lorsqu'une ressource n'est pas trouvée."""

    def __init__(self, message, resource_type=None, resource_id=None):
        super().__init__(message)
        self.message = message
        self.resource_type = resource_type
        self.resource_id = resource_id


class UnauthorizedError(Exception):
    """Exception levée lors d'erreurs d'autorisation."""

    def __init__(self, message, user_id=None, required_permission=None):
        super().__init__(message)
        self.message = message
        self.user_id = user_id
        self.required_permission = required_permission


class BusinessLogicError(Exception):
    """Exception levée lors d'erreurs de logique métier."""

    def __init__(self, message, error_code=None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ConfigurationError(Exception):
    """Exception levée lors d'erreurs de configuration."""

    def __init__(self, message, config_key=None):
        super().__init__(message)
        self.message = message
        self.config_key = config_key
