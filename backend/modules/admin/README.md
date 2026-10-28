# Module d'Administration

Ce module fournit des fonctionnalités d'administration pour gérer les utilisateurs et les paramètres système.

## Fonctionnalités

- Gestion des utilisateurs (liste, activation/désactivation)
- Réinitialisation de la 2FA
- Interface d'administration avec Flask-Admin

## Configuration

### Prérequis

- Python 3.8+
- Flask
- Flask-Login
- Flask-Admin

### Installation

1. S'assurer que les dépendances sont installées :
   ```bash
   pip install -r requirements.txt
   ```

2. Importer et initialiser le module dans votre application :
   ```python
   from backend.modules.admin import init_app
   
   app = Flask(__name__)
   # ... configuration de l'application ...
   
   # Initialiser le module admin
   init_app(app)
   ```

## API Endpoints

### Liste des utilisateurs
- **URL** : `/admin/users`
- **Méthode** : `GET`
- **Authentification** : Requise (Admin)
- **Réponse** : Liste des utilisateurs avec leurs informations

### Activer/Désactiver un utilisateur
- **URL** : `/admin/users/<int:user_id>/toggle`
- **Méthode** : `POST`
- **Authentification** : Requise (Admin)
- **Paramètres** :
  - `user_id` (dans l'URL) : ID de l'utilisateur à modifier

### Réinitialiser la 2FA d'un utilisateur
- **URL** : `/admin/users/<int:user_id>/reset-2fa`
- **Méthode** : `POST`
- **Authentification** : Requise (Admin)
- **Paramètres** :
  - `user_id` (dans l'URL) : ID de l'utilisateur

## Interface d'administration

L'interface d'administration est accessible à l'adresse `/admin/console` et fournit une interface graphique pour gérer :

- Utilisateurs
- Rôles
- Permissions
- Transactions
- Catégories
- Comptes

## Sécurité

- Toutes les routes d'API nécessitent une authentification
- Seuls les utilisateurs avec le rôle d'administrateur peuvent accéder à ces fonctionnalités
- La 2FA est fortement recommandée pour les comptes administrateurs

## Développement

### Structure des dossiers

```
admin/
├── __init__.py      # Initialisation du module
├── commands.py      # Commandes CLI
├── routes.py        # Routes d'API
├── services.py      # Logique métier
├── views.py         # Vues Flask-Admin
└── tests/           # Tests unitaires et d'intégration
```

### Exécution des tests

```bash
pytest backend/modules/admin/tests/
```

## Licence

[À spécifier selon la licence du projet]
