"""
Nettoyage des données de démonstration.
"""

from core.models.account import Account
from core.models.category import Category
from core.models.transactions import Transaction
from core.models.user import User

from .. import create_app, db


def cleanup_demo_data():
    """Nettoie toutes les données de démonstration."""
    app = create_app()
    with app.app_context():
        try:
            # Supprimer d'abord toutes les transactions
            Transaction.query.delete()

            # Puis les catégories
            Category.query.delete()

            # Puis les comptes
            Account.query.delete()

            # Enfin l'utilisateur de démo s'il existe
            demo_user = User.query.filter_by(email="demo@example.com").first()
            if demo_user:
                db.session.delete(demo_user)

            db.session.commit()
            print("✅ Nettoyage des données de démonstration terminé avec succès.")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors du nettoyage des données : {str(e)}")
            return False


if __name__ == "__main__":
    cleanup_demo_data()
