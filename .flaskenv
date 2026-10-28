# Configuration de base de Flask
FLASK_APP=backend/wsgi.py
FLASK_ENV=development
FLASK_DEBUG=1

# Configuration de la base de données (voir .env pour DATABASE_URL)
SQLALCHEMY_TRACK_MODIFICATIONS=False

# Configuration du serveur
HOST=0.0.0.0
PORT=5000

# Clé secrète pour les sessions
# SECRET_KEY=  # Definir dans .env

# Configuration des emails (à adapter en production)
MAIL_SERVER=localhost
MAIL_PORT=1025  # MailHog par défaut
MAIL_USE_TLS=False
MAIL_USE_SSL=False
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=noreply@example.com

# Configuration de la pagination
ITEMS_PER_PAGE=20

# Configuration du cache
CACHE_TYPE=SimpleCache
CACHE_DEFAULT_TIMEOUT=300

# Configuration de l'API
API_PREFIX=/api/v1
API_TITLE=API Gestion Budgétaire
API_VERSION=1.0.0

# Configuration Babel
BABEL_DEFAULT_LOCALE=fr
BABEL_DEFAULT_TIMEZONE=Europe/Paris
LANGUAGES=['fr', 'en']

# Configuration JWT
# JWT_SECRET_KEY=  # Definir dans .env
JWT_ACCESS_TOKEN_EXPIRES=3600  # 1 heure
JWT_REFRESH_TOKEN_EXPIRES=2592000  # 30 jours

# Configuration CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_SUPPORTS_CREDENTIALS=True

# Configuration du taux de requêtes
RATELIMIT_DEFAULT=200 per day;50 per hour

# Configuration de l'application
APP_NAME="Gestion Budgétaire"
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB
