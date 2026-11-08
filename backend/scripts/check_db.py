from sqlalchemy import text

from app import create_app
from core.extensions import db


def check_database():
    app = create_app()

    with app.app_context():
        # Afficher les tables
        print("=== Tables dans la base de données ===")
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(tables)

        # Vérifier si la table users existe
        if "users" in tables:
            # Compter les utilisateurs
            print("\n=== Nombre d'utilisateurs enregistrés ===")
            result = db.session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"Nombre d'utilisateurs: {count}")

            # Afficher les 10 premiers utilisateurs
            if count > 0:
                print("\n=== Détails des utilisateurs (10 premiers) ===")
                users = db.session.execute(
                    text("SELECT id, email, username, is_active FROM users LIMIT 10")
                ).fetchall()
                for user in users:
                    print(
                        f"ID: {user[0]}, Email: {user[1]}, Pseudo: {user[2]}, Actif: {user[3]}"
                    )
        else:
            print("\nLa table 'users' n'existe pas dans la base de données.")


if __name__ == "__main__":
    check_database()
