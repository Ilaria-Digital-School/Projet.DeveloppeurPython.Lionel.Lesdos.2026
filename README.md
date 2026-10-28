# Application de Gestion de Budget Personnel

Application web de gestion budgetaire personnelle permettant le suivi des comptes bancaires, des transactions et des budgets. Projet realise dans le cadre du Titre Professionnel DWWM (Bloc 2).

## Fonctionnalites

- **Gestion multi-comptes** : comptes courants, epargne, carte credit, suivi des soldes en temps reel
- **Transactions** : creation, modification, suppression avec categorisation et filtres avances (par compte, categorie, type, periode)
- **Categories** : organisation des depenses et revenus par categories personnalisables
- **Budgets** : definition d'objectifs budgetaires par categorie avec suivi de progression et alertes
- **Transactions recurrentes** : programmation de virements, prelevements et revenus periodiques
- **Dashboard** : tableaux de bord avec graphiques (Chart.js), repartition des depenses, tendances mensuelles
- **Rapports** : generation de rapports PDF et export des donnees (CSV, Excel)
- **Import/Export** : import de releves bancaires, export des donnees
- **Authentification** : inscription, connexion securisee, gestion des sessions, roles et permissions, 2FA (TOTP et email)
- **Administration** : interface d'administration pour la gestion des utilisateurs et le monitoring
- **API REST v1** : 107 routes sous `/api/v1/` reparties en 14 modules

## Technologies

| Composant        | Technologie                            |
|------------------|----------------------------------------|
| Backend          | Python 3.14, Flask 3.1                 |
| ORM              | SQLAlchemy 2.0, Alembic (migrations)   |
| Base de donnees  | PostgreSQL 18                          |
| Authentification | Flask-Login, Flask-JWT-Extended, hachage PBKDF2-SHA256 (Werkzeug) |
| Frontend         | Jinja2, Tailwind CSS, Chart.js         |
| Formulaires      | Flask-WTF, WTForms                     |
| Validation       | Pydantic                               |
| Securite         | CSRF (Flask-WTF), CORS, Rate Limiting  |
| Tests            | Pytest, pytest-cov, Factory Boy, Faker |
| Deploiement      | Docker, Gunicorn, Nginx                |

## Architecture

```
Appli_Web_Budget/
├── backend/
│   ├── api/v1/                # API REST v1 (107 routes, 14 modules)
│   ├── app/                   # Factory Flask et configuration
│   ├── core/
│   │   ├── models/            # Modeles SQLAlchemy (User, Account, Transaction, Category, Budget...)
│   │   ├── services/          # Logique metier (AccountService, TransactionService...)
│   │   ├── schemas/           # Schemas Pydantic (validation API)
│   │   ├── security/          # Securite (2FA TOTP, email, appareils)
│   │   ├── extensions.py      # Extensions Flask (db, login, jwt, csrf)
│   │   └── decorators.py      # @admin_required
│   ├── modules/               # Modules fonctionnels (blueprints Flask)
│   │   ├── auth/              # Authentification (login, register, logout)
│   │   ├── accounts/          # CRUD comptes bancaires
│   │   ├── transactions/      # CRUD transactions + recurrentes
│   │   ├── categories/        # CRUD categories
│   │   ├── dashboard/         # Tableaux de bord et analytics
│   │   ├── reports/           # Generation de rapports
│   │   ├── profile/           # Profil utilisateur et 2FA
│   │   ├── settings/          # Parametres
│   │   ├── notifications/     # Notifications
│   │   ├── import_export/     # Import/export donnees
│   │   ├── admin/             # Administration et monitoring
│   │   └── ...
│   ├── commands/              # Commandes CLI Flask
│   ├── migrations/            # Migrations Alembic
│   ├── scripts/               # Scripts utilitaires
│   └── tests/                 # Tests unitaires, integration et fonctionnels
├── frontend/
│   ├── templates/             # Templates Jinja2
│   └── static/                # CSS, JavaScript, images
├── docs/                      # Documentation technique et diagrammes UML
├── Dockerfile                 # Image Docker
├── docker-compose.yml         # Orchestration des services
└── .github/workflows/         # CI/CD GitHub Actions
```

## Installation

> **Note** : L'application utilise PostgreSQL comme unique SGBD (dev, test, prod).

### Installation rapide (script assiste)

```bash
git clone git@github.com:Ilaria-Digital-School/Projet.DeveloppeurPython.Lionel.Lesdos.2026.git Appli_Web_Budget
cd Appli_Web_Budget

# Installation interactive (choix Docker ou local)
./setup.sh

# Ou directement :
./setup.sh --docker   # Mode Docker (recommande)
./setup.sh --local    # Mode developpement local
```

Le script genere automatiquement les cles secretes, cree le `.env`, et configure PostgreSQL.

---

### A. Avec Docker (recommande)

**Prerequis** : Docker, Docker Compose V2

```bash
# Cloner le depot
git clone git@github.com:Ilaria-Digital-School/Projet.DeveloppeurPython.Lionel.Lesdos.2026.git Appli_Web_Budget
cd Appli_Web_Budget

# Configurer l'environnement
cp .env.example .env
# Editer .env : generer SECRET_KEY, JWT_SECRET_KEY, WTF_CSRF_SECRET_KEY, SECURITY_PASSWORD_SALT
# Definir POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
# DATABASE_URL=postgresql://USER:PASSWORD@db:5432/DB_NAME

# Lancer les services (PostgreSQL + Redis + App)
docker compose up --build -d

# Appliquer les migrations
docker compose exec app flask db upgrade

# Creer un administrateur
docker compose exec app flask create-admin
```

L'application (Gunicorn) ecoute sur le port 5000 a l'interieur du reseau Docker (port non publie sur l'hote) : l'acces se fait via le reverse proxy Nginx externe, relie par le reseau `proxy_network`.

---

### B. Sans Docker (developpement local)

**Prerequis** : Python 3.10+, PostgreSQL 14+ installe localement

```bash
# Cloner le depot
git clone git@github.com:Ilaria-Digital-School/Projet.DeveloppeurPython.Lionel.Lesdos.2026.git Appli_Web_Budget
cd Appli_Web_Budget

# Creer la base de donnees PostgreSQL
sudo -u postgres psql -c "CREATE USER budget_user WITH PASSWORD 'votre_mot_de_passe';"
sudo -u postgres psql -c "CREATE DATABASE budget OWNER budget_user;"
sudo -u postgres psql -c "CREATE DATABASE budget_test OWNER budget_user;"

# Configurer l'environnement
cp .env.example .env
# Editer .env : generer les cles secretes et definir DATABASE_URL
# DATABASE_URL=postgresql://budget_user:votre_mot_de_passe@localhost:5432/budget

# Creer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dependances
pip install -r backend/requirements.txt

# Appliquer les migrations
cd backend
flask db upgrade

# Creer un administrateur
flask create-admin

# Lancer le serveur de developpement
flask run --debug --port 8080
```

---

### C. Demo en ligne

| | |
|---|---|
| **URL** | https://example.com |
| **Email** | demo@budget.fr |
| **Mot de passe** | DemoBudget2026! |

> Compte de demonstration avec donnees deterministes, reinitialisable via `backend/scripts/create_demo_user.py`.

## Tests

```bash
cd backend
python3 -m pytest --tb=short -q        # 185 tests
pytest --cov=. tests/                   # Avec couverture de code
pytest tests/unit/                      # Tests unitaires uniquement
pytest tests/integration/               # Tests d'integration uniquement
```

## Documentation

La documentation technique de developpement est disponible dans le dossier `docs/` :

- **API REST v1** : `docs/API_README.md` (107 routes documentees)
- **Architecture** : `docs/ARCHITECTURE.md`
- **Commandes** : `docs/COMMANDS.md`
- **Compte de demonstration** : `docs/README_DEMO.md`
- **Notifications** : `docs/README_NOTIFICATIONS.md`

Les diagrammes UML (MCD, MLD, MPD, classes, sequences, architecture), les guides,
le plan de test et le suivi des fonctionnalites font partie des livrables de
formation, hors du depot applicatif.

## Auteur

**Lionel** - Developpeur Web et Web Mobile
Projet realise dans le cadre du Titre Professionnel DWWM - Bloc 2

## Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de details.
