# Architecture du Projet

## Vue d'ensemble

L'application suit une architecture modulaire en couches avec une separation claire entre le frontend et le backend. Le backend est construit avec Flask en architecture MVC, avec une API REST v1 dediee au frontend JavaScript.

## Structure des Repertoires

```
Appli_Web_Budget/
├── backend/                 # Toute la logique serveur
│   ├── api/                # API REST v1
│   │   └── v1/             # 107 routes, 14 modules
│   │       ├── helpers.py  # api_success(), api_error(), api_paginated()
│   │       ├── auth.py     # 8 routes (login JWT, register, refresh, etc.)
│   │       ├── accounts.py # 7 routes (CRUD + import/export)
│   │       ├── categories.py # 5 routes (CRUD)
│   │       ├── transactions.py # 8 routes (CRUD + bulk + import/export)
│   │       ├── budgets.py  # 10 routes (CRUD + alertes + seuils)
│   │       ├── dashboard.py # 8 routes (summary + graphiques)
│   │       ├── reports.py  # 7 routes (generation + export PDF)
│   │       ├── recurring.py # 6 routes (CRUD + pause)
│   │       ├── profile.py  # 11 routes (photo + 2FA TOTP/email)
│   │       ├── settings.py # 8 routes (parametres + password + export)
│   │       ├── notifications.py # 4 routes (liste, non lues, marquer lu/tout lu)
│   │       ├── devices.py  # 5 routes (liste, detail, revocation, historique, heartbeat)
│   │       ├── admin.py    # 14 routes (stats + users + monitoring)
│   │       └── users.py    # 6 routes (profil + roles, JWT)
│   │
│   ├── app/                # Point d'entree de l'application
│   │   ├── __init__.py     # Factory create_app() + enregistrement blueprints
│   │   └── config/         # Configuration (dev, prod, test)
│   │
│   ├── core/               # Fonctionnalites centrales
│   │   ├── models/         # Modeles de donnees SQLAlchemy
│   │   ├── services/       # Services de logique metier
│   │   ├── schemas/        # Schemas de validation Pydantic
│   │   ├── security/       # 2FA (TOTP, email), gestion appareils
│   │   ├── extensions.py   # Extensions Flask (db, login, jwt, csrf, etc.)
│   │   └── decorators.py   # @admin_required
│   │
│   ├── modules/            # Modules fonctionnels (Blueprints web)
│   │   ├── auth/           # Authentification (login, register, logout)
│   │   ├── accounts/       # Gestion des comptes
│   │   ├── transactions/   # Gestion des transactions
│   │   ├── categories/     # Gestion des categories
│   │   ├── dashboard/      # Tableau de bord
│   │   ├── reports/        # Rapports
│   │   ├── profile/        # Profil utilisateur
│   │   ├── settings/       # Parametres
│   │   ├── notifications/  # Notifications
│   │   ├── devices/        # Appareils connectes
│   │   ├── import_export/  # Import/export donnees
│   │   ├── admin/          # Administration
│   │   └── main/           # Page d'accueil
│   │
│   ├── commands/           # Commandes CLI Flask
│   ├── scripts/            # Scripts utilitaires
│   ├── tests/              # Tests automatises (185 tests)
│   └── migrations/         # Migrations Alembic
│
└── frontend/               # Logique client
    ├── static/
    │   ├── css/            # Tailwind CSS + styles personnalises par page
    │   ├── js/pages/       # JavaScript par page (dashboard, transactions, etc.)
    │   └── img/            # Images et icones
    │
    └── templates/          # Templates Jinja2
        ├── base.html       # Template de base
        ├── auth/           # Pages d'authentification
        ├── admin/          # Pages d'administration
        └── ...             # Autres pages
```

## Flux de Donnees

### Architecture en couches

```
Client (navigateur)
    |
    | HTTP/HTTPS (AJAX JSON)
    v
Nginx (reverse proxy, SSL)
    |
    v
Gunicorn (WSGI)
    |
    v
Flask Application
    |
    +-- API v1 (/api/v1/*)        --> Reponses JSON (pour le JS frontend)
    +-- Modules web (Blueprints)  --> Reponses HTML (templates Jinja2)
    |
    v
Services (logique metier)
    |
    v
Modeles SQLAlchemy (ORM)
    |
    v
PostgreSQL (dev, test, prod)
```

### Flux d'une requete type

1. **Requete HTTP** → Nginx (en production, SSL termination)
2. **WSGI** → Gunicorn → Application Flask
3. **Routage** → Blueprint API v1 ou module web
4. **Authentification** → Flask-Login (session) ou JWT (API)
5. **CSRF** → Verification du token X-CSRFToken
6. **Traitement** → Service metier
7. **Acces aux donnees** → Modeles SQLAlchemy / ORM
8. **Reponse** → JSON (API) ou HTML (templates Jinja2)

## Securite

- **Authentification web** : Flask-Login avec sessions serveur
- **Authentification API** : JWT (Flask-JWT-Extended) avec access/refresh tokens
- **Autorisation** : Roles et permissions, decorateur `@admin_required`
- **Validation** : Pydantic pour l'API, WTForms pour les formulaires
- **Protection CSRF** : Flask-WTF, token dans `<meta name="csrf-token">` + header `X-CSRFToken`
- **Mots de passe** : Hachage PBKDF2-SHA256 (Werkzeug), verification retrocompatible bcrypt/scrypt
- **2FA** : TOTP (Google Authenticator) et code par email
- **Rate limiting** : Protection contre les attaques par force brute

## Base de Donnees

- **SGBD** : PostgreSQL (unique SGBD : dev, test, production)
- **ORM** : SQLAlchemy 2.0
- **Migrations** : Alembic (Flask-Migrate)
- **Conventions** : Colonnes en francais (montant, libelle, type_transaction, etc.)

## Tests

- **Tests unitaires** : Modeles et services (pytest)
- **Tests d'integration** : Routes et API (pytest + Flask test client)
- **Tests fonctionnels** : Scenarios end-to-end
- **Couverture de code** : pytest-cov
- **Fixtures** : Factory Boy + Faker
- **Total** : 185 tests

## Deploiement

### Developpement

```bash
cd backend
flask run --debug --port 8080
```

### Production

- **Serveur WSGI** : Gunicorn
- **Reverse proxy** : Nginx avec SSL
- **Conteneurisation** : Docker + Docker Compose
- **URL** : https://example.com

```bash
docker compose up --build -d
```

## Documentation

- `docs/API_README.md` : Documentation API REST v1 (107 routes)
- `docs/COMMANDS.md` : Commandes CLI et scripts
- `docs/README_DEMO.md` : Compte de demonstration
- `docs/README_NOTIFICATIONS.md` : Systeme de notifications

Les diagrammes UML (MCD, MLD, classes, sequences, architecture), les guides,
le plan de test et le suivi des fonctionnalites font partie des livrables de
formation, hors du depot applicatif. L'installation est documentee dans le
README racine.
