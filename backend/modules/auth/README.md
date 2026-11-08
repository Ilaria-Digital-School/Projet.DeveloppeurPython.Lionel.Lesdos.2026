# Module d'Authentification

Ce module gère l'authentification et l'autorisation des utilisateurs dans l'application.

## Fonctionnalités

- Authentification des utilisateurs (connexion/déconnexion)
- Gestion des jetons JWT (accès et rafraîchissement)
- Gestion des rôles et des permissions
- Sécurité des mots de passe
- Protection des routes avec authentification

## Structure du module

```
auth/
├── __init__.py          # Initialisation du module
├── api/                 # Points d'entrée de l'API
│   ├── __init__.py
│   ├── auth_routes.py   # Routes d'authentification
│   └── role_routes.py   # Gestion des rôles et permissions
├── services/            # Logique métier
│   ├── __init__.py
│   └── role_service.py  # Service de gestion des rôles
└── tests/               # Tests automatisés
    ├── conftest.py     # Configuration des tests
    └── unit/           # Tests unitaires
        └── test_role_service.py
```

## Installation et configuration

1. **Configuration requise**
   - Python 3.8+
   - Flask
   - Flask-JWT-Extended
   - SQLAlchemy

2. **Installation**
   
   Le module est automatiquement installé avec l'application principale.

3. **Configuration**

   Ajoutez la configuration suivante à votre fichier de configuration :

   ```python
   # Configuration JWT
   JWT_SECRET_KEY = 'votre-clé-secrète'  # À remplacer en production
   JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
   JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
   ```

## Utilisation

### Authentification

#### Connexion

```http
POST /auth/login
Content-Type: application/json

{
  "email": "utilisateur@example.com",
  "password": "motdepasse"
}
```

#### Rafraîchissement du token

```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

### Gestion des rôles

#### Lister les rôles

```http
GET /api/roles
Authorization: Bearer <access_token>
```

#### Créer un rôle

```http
POST /api/roles
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "moderator",
  "description": "Modérateur du site"
}
```

## Tests

Pour exécuter les tests du module :

```bash
pytest backend/modules/auth/tests/
```

## Sécurité

- Les mots de passe sont hachés avec bcrypt avant d'être stockés
- Utilisation de JWT pour l'authentification sans état
- Protection contre les attaques par force brute
- Validation des entrées utilisateur

## Dépendances

- `Flask-JWT-Extended` : Gestion des jetons JWT
- `passlib` : Hachage des mots de passe
- `python-jose` : Manipulation des jetons JWT

## Licence

Ce module fait partie du projet Appli_Web_Budget et est sous licence MIT.
