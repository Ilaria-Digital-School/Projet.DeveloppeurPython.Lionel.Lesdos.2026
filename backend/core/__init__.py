def init_models():
    """Importe tous les modèles pour les enregistrer avec SQLAlchemy."""
    from .models import budget  # Modèle budget
    from .models import category  # Modèle catégorie
    from .models import transactions  # Modèle transaction
    from .models import user  # Modèle utilisateur
    from .models import (
        account,
        associations,
        budget_history,
        device,
        email,
        import_export,
        notification,
        notification_preference,
        permission,
        recurring_transaction,
        report,
        role,
        security_event,
        session,
        setting,
        token_blacklist,
    )

    # Les imports ci-dessus enregistrent automatiquement les modèles avec SQLAlchemy
    # grâce aux imports dans models/__init__.py
