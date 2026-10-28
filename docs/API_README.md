# API REST v1 — Documentation

Base URL : `/api/v1`

## Documentation interactive (Swagger UI)

Une fois authentifie, l'API est explorable en ligne :

- **Swagger UI** : `/api/v1/docs`
- **Specification OpenAPI 3.0** : `/api/v1/openapi.json` (catalogue auto-genere
  depuis les routes ; resumes tires des docstrings)

## Authentification

Deux modes d'authentification sont supportes :

- **Session (web)** : Cookie de session Flask-Login via `/auth/login` (pages HTML)
- **JWT (API)** : Token Bearer via `POST /api/v1/auth/login`

Les routes protegees par `@login_required` acceptent les sessions web.
Les routes protegees par `@jwt_required()` necessitent un header :

```
Authorization: Bearer <access_token>
```

### Protection CSRF

Les requetes POST/PUT/DELETE necessitent le header CSRF :

```
X-CSRFToken: <token>
```

Le token est disponible dans la balise `<meta name="csrf-token">` des pages HTML.

## Format des reponses

### Succes

```json
{
  "status": "success",
  "data": { ... }
}
```

### Succes avec message

```json
{
  "status": "success",
  "message": "Operation reussie",
  "data": { ... }
}
```

### Succes pagine

```json
{
  "status": "success",
  "data": { ... },
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8
  }
}
```

### Erreur

```json
{
  "status": "error",
  "message": "Description de l'erreur"
}
```

### Codes HTTP

| Code | Usage |
|------|-------|
| 200 | OK |
| 201 | Cree |
| 400 | Requete invalide |
| 401 | Non authentifie |
| 403 | Acces interdit |
| 404 | Ressource introuvable |
| 409 | Conflit (ex: categorie utilisee) |
| 500 | Erreur serveur |

---

## 1. Auth (`/api/v1/auth`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| POST | `/auth/login` | — | Connexion JWT (etape 1 si 2FA activee) |
| POST | `/auth/2fa/verify` | Jeton 2FA | Connexion JWT, etape 2 : code 2FA |
| POST | `/auth/register` | — | Inscription |
| POST | `/auth/refresh` | JWT refresh | Rafraichir le token |
| POST | `/auth/logout` | JWT | Deconnexion (invalide le token) |
| GET | `/auth/user` | JWT | Utilisateur courant |
| GET | `/auth/check` | Session | Verifier l'etat d'authentification |
| POST | `/auth/2fa/resend` | Session | Renvoyer un code 2FA TOTP |
| POST | `/auth/2fa/resend-email` | Session | Renvoyer un code 2FA par email |

### POST `/auth/login`

```json
// Request
{ "email": "user@example.com", "password": "..." }

// Response 200 (compte sans 2FA)
{
  "status": "success",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": { "id": 1, "username": "...", "email": "..." }
}

// Response 200 (compte avec 2FA) : aucun jeton, le code est envoye par
// email si c'est la methode du compte
{
  "status": "success",
  "two_factor_required": true,
  "two_factor_method": "email",        // ou "app" (TOTP)
  "two_factor_token": "eyJ1aWQiOjF9...", // valable 10 minutes
  "code_sent": true
}
```

Erreurs : `401` identifiants invalides, `429` compte verrouille (5 echecs,
15 minutes).

### POST `/auth/2fa/verify`

Etape 2 de la connexion pour un compte avec 2FA.

```json
// Request (code, ou backup_code a la place)
{ "two_factor_token": "eyJ1aWQiOjF9...", "code": "123456" }

// Response 200 : memes champs que /auth/login sans 2FA
{ "status": "success", "access_token": "eyJ...", "refresh_token": "eyJ...", "user": { ... } }
```

Erreurs : `401` jeton invalide ou expire, ou code faux (chaque code faux
compte comme un echec de connexion) ; `429` compte verrouille.

### POST `/auth/register`

```json
// Request
{ "username": "newuser", "email": "new@example.com", "password": "..." }

// Response 201
{ "status": "success", "data": { "user": { "id": 2, ... } } }
```

---

## 2. Comptes (`/api/v1/comptes`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/comptes` | Session | Liste des comptes |
| POST | `/comptes` | Session | Creer un compte |
| GET | `/comptes/<id>` | Session | Detail d'un compte |
| PUT | `/comptes/<id>` | Session | Modifier un compte |
| DELETE | `/comptes/<id>` | Session | Supprimer un compte |
| POST | `/comptes/import` | Session | Importer depuis CSV |
| GET | `/comptes/export` | Session | Exporter en CSV |

### POST `/comptes`

```json
// Request
{
  "name": "Compte Courant",
  "account_type": "checking",  // checking, savings, credit_card, cash, investment, loan, other
  "initial_balance": 1500.00,
  "currency": "EUR",
  "bank_name": "BNP",          // optionnel
  "iban": "FR76...",            // optionnel
  "bic_swift": "BNPAFRPP"      // optionnel
}

// Response 201
{ "status": "success", "data": { "account_id": 1, "message": "..." } }
```

### GET `/comptes/export`

Parametres query : `account_id`, `date_from` (YYYY-MM-DD), `date_to`, `format` (csv/xlsx), `include_transactions` (true/false), `include_account_details` (true/false)

Retourne un fichier CSV ou Excel.

---

## 3. Categories (`/api/v1/categories`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/categories` | Session | Liste des categories |
| POST | `/categories` | Session | Creer une categorie |
| GET | `/categories/<id>` | Session | Detail d'une categorie |
| PUT | `/categories/<id>` | Session | Modifier une categorie |
| DELETE | `/categories/<id>` | Session | Supprimer une categorie |

### POST `/categories`

```json
// Request
{
  "name": "Alimentation",
  "type": "expense",           // expense, income, transfer
  "color": "#FF5733",
  "icon": "fa-shopping-cart",
  "description": "Courses"     // optionnel
}

// Response 201
{
  "status": "success",
  "data": {
    "id": 1, "name": "Alimentation", "type": "expense",
    "color": "#FF5733", "icon": "fa-shopping-cart"
  }
}
```

### DELETE `/categories/<id>`

Parametres query : `force=1` pour forcer la suppression d'une categorie avec transactions (reaffecte les transactions a la categorie par defaut).

Sans `force`, retourne `409` si la categorie a des transactions.

---

## 4. Transactions (`/api/v1/transactions`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/transactions` | Session | Liste paginee et filtree |
| POST | `/transactions` | Session | Creer une transaction |
| GET | `/transactions/<id>` | Session | Detail d'une transaction |
| PUT | `/transactions/<id>` | Session | Modifier une transaction |
| DELETE | `/transactions/<id>` | Session | Supprimer une transaction |
| POST | `/transactions/bulk-delete` | Session | Suppression en masse (max 200) |
| POST | `/transactions/import` | Session | Importer depuis CSV |
| GET | `/transactions/export` | Session | Exporter en CSV/Excel/PDF |

### GET `/transactions`

Parametres query :
- `page` (default: 1), `per_page` (default: 20)
- `account` : ID du compte
- `category` : ID de la categorie
- `type` : income / expense / transfer
- `date_from`, `date_to` : format DD/MM/YYYY

### POST `/transactions`

```json
// Request
{
  "type": "achat",             // achat, salaire, virement, etc.
  "amount": 42.50,
  "date": "2026-05-03",       // format YYYY-MM-DD
  "description": "Courses",
  "account_id": 1,
  "category_id": 3,           // optionnel
  "notes": ""                  // optionnel
}

// Response 201
{ "status": "success", "data": { "transaction_id": 1, "message": "..." } }
```

### POST `/transactions/bulk-delete`

```json
// Request
{ "transaction_ids": [1, 2, 3] }

// Response 200
{
  "status": "success",
  "data": { "deleted_count": 3, "total_requested": 3, "message": "..." }
}
```

---

## 5. Budgets (`/api/v1/budgets`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/budgets` | Session | Liste paginee des budgets |
| POST | `/budgets` | Session | Creer un budget |
| GET | `/budgets/<id>` | Session | Detail d'un budget |
| PUT | `/budgets/<id>` | Session | Modifier un budget |
| DELETE | `/budgets/<id>` | Session | Supprimer un budget |
| GET | `/budgets/alerts` | Session | Alertes budgetaires |
| GET | `/budgets/summary` | Session | Resume pour le dashboard |
| GET | `/budgets/export` | Session | Exporter les budgets |
| GET | `/budgets/threshold` | Session | Seuil d'alerte par defaut |
| POST | `/budgets/threshold` | Session | Definir le seuil d'alerte |

### POST `/budgets`

```json
// Request
{
  "category_id": 3,
  "amount": 500.00,
  "period": "monthly",        // monthly, yearly, custom
  "start_date": "2026-05-01",
  "notification_threshold": 90 // optionnel, pourcentage 1-100
}

// Response 201
{ "status": "success", "data": { "budget": { ... } }, "message": "..." }
```

### POST `/budgets/threshold`

```json
// Request
{ "default_threshold": 85, "update_existing": true }

// Response 200
{ "status": "success", "data": { "threshold": 85, "budgets_updated": 5 } }
```

---

## 6. Dashboard (`/api/v1/dashboard`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/dashboard/summary` | Session | Resume financier |
| GET | `/dashboard/export` | Session | Export des donnees |
| POST | `/dashboard/preferences` | Session | Preferences d'affichage |
| GET | `/dashboard/charts/balance-evolution` | Session | Evolution des soldes |
| GET | `/dashboard/charts/expenses-breakdown` | Session | Repartition des depenses |
| GET | `/dashboard/charts/income-vs-expenses` | Session | Revenus vs depenses |
| GET | `/dashboard/charts/budget-progress` | Session | Progression budgets |
| GET | `/dashboard/charts/kpis` | Session | KPIs financiers |

### GET `/dashboard/summary`

```json
// Response 200
{
  "status": "success",
  "data": {
    "stats": {
      "budget_count": 5,
      "total_budget": 2500.0,
      "monthly_income": 3000.0,
      "monthly_expenses": 1800.0,
      "balance": 15000.0
    },
    "recent_transactions": [
      { "id": 1, "amount": 42.50, "description": "...", "date": "2026-05-03", "category": "..." }
    ],
    "budgets": [
      { "id": 1, "amount": 500.0, "spent": 320.0, "category": "...", "period": "monthly" }
    ],
    "expenses_by_category": [ ... ]
  }
}
```

### Parametres des graphiques

| Route | Param | Default | Description |
|-------|-------|---------|-------------|
| `balance-evolution` | `months` | 6 | Nombre de mois |
| `expenses-breakdown` | `period` | 30 | Nombre de jours |
| `income-vs-expenses` | `months` | 12 | Nombre de mois |

---

## 7. Rapports (`/api/v1/rapports`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/rapports` | Session | Liste des rapports sauvegardes |
| POST | `/rapports/generate` | Session | Generer un rapport |
| GET | `/rapports/data` | Session | Donnees pour graphiques frontend |
| GET | `/rapports/<id>` | Session | Detail d'un rapport |
| DELETE | `/rapports/<id>` | Session | Supprimer un rapport |
| GET | `/rapports/export` | Session | Export multi-format (pdf, excel, csv, json) |
| GET | `/rapports/export/pdf` | Session | Export PDF |

### POST `/rapports/generate`

```json
// Request
{
  "report_type": "monthly",    // monthly, category, trends, comparison
  "date_range": "last_month",  // this_month, last_month, last_3_months, custom
  "start_date": "2026-01-01",  // si date_range=custom
  "end_date": "2026-03-31",
  "name": "Mon rapport"        // optionnel
}
```

**Note** : Necessite pandas/matplotlib/seaborn (installes en Docker uniquement).

---

## 8. Transactions recurrentes (`/api/v1/recurring`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/recurring` | Session | Liste des recurrences |
| POST | `/recurring` | Session | Creer une recurrence |
| GET | `/recurring/<id>` | Session | Detail d'une recurrence |
| PUT | `/recurring/<id>` | Session | Modifier une recurrence |
| DELETE | `/recurring/<id>` | Session | Supprimer une recurrence |
| POST | `/recurring/<id>/pause` | Session | Basculer pause/actif |

Parametres query : `include_inactive=true` pour inclure les recurrences en pause.

---

## 9. Profil (`/api/v1/profil`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| POST | `/profil/picture` | Session | Upload photo de profil |
| POST | `/profil/notifications` | Session | Preferences de notification |
| POST | `/profil/2fa/enable` | Session | Activer 2FA TOTP |
| POST | `/profil/2fa/verify` | Session | Verifier code 2FA |
| POST | `/profil/2fa/disable` | Session | Desactiver 2FA |
| GET | `/profil/2fa/backup-codes` | Session | Codes de secours restants |
| POST | `/profil/2fa/regenerate-backup-codes` | Session | Regenerer codes |
| GET | `/profil/2fa/status` | Session | Statut 2FA complet |
| POST | `/profil/email-2fa/send-code` | Session | Envoyer code email 2FA |
| POST | `/profil/email-2fa/verify-code` | Session | Verifier code email |
| POST | `/profil/email-2fa/disable` | Session | Desactiver email 2FA |

### POST `/profil/picture`

Multipart form avec champ `profile_picture`. Formats acceptes : PNG, JPG, GIF, WEBP. Taille max : 5 Mo. Validation des magic bytes.

### GET `/profil/2fa/status`

```json
// Response 200
{
  "status": "success",
  "data": {
    "two_factor_enabled": true,
    "totp_enabled": true,
    "email_2fa_enabled": false,
    "backup_codes_count": 8
  }
}
```

---

## 10. Parametres (`/api/v1/settings`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/settings` | Session | Tous les parametres |
| PUT | `/settings` | Session | Modifier parametres generaux |
| POST | `/settings/password` | Session | Changer le mot de passe |
| GET | `/settings/export` | Session | Exporter les donnees utilisateur |
| DELETE | `/settings/account` | Session | Supprimer le compte |
| GET | `/settings/notifications` | Session | Preferences de notification |
| POST | `/settings/notifications` | Session | Modifier notifications |

### POST `/settings/password`

```json
// Request
{ "current_password": "...", "new_password": "..." }
```

Le mot de passe doit faire au moins 8 caracteres.

### DELETE `/settings/account`

```json
// Request (confirmation par mot de passe)
{ "password": "..." }
```

Supprime l'utilisateur et toutes ses donnees (comptes, transactions, categories).

---

## 11. Notifications (`/api/v1/notifications`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/notifications` | Session | Liste paginee des notifications (`?unread_only=true`) |
| GET | `/notifications/unread-count` | Session | Nombre de notifications non lues |
| POST | `/notifications/mark-as-read/<id>` | Session | Marquer comme lue |
| POST | `/notifications/mark-all-read` | Session | Tout marquer comme lu |

---

## 12. Appareils (`/api/v1/devices`)

| Methode | URL | Auth | Description |
|---------|-----|------|-------------|
| GET | `/devices` | Session | Liste des appareils de l'utilisateur |
| GET | `/devices/<public_id>` | Session | Details d'un appareil |
| DELETE | `/devices/<public_id>` | Session | Revoquer un appareil |
| GET | `/devices/<public_id>/history` | Session | Historique de connexion |
| POST | `/devices/heartbeat` | Session | Heartbeat appareil |

```json
// Request
{ "device_id": "abc123", "metadata": { ... } }
```

---

## 13. Administration (`/api/v1/admin`)

Toutes les routes admin necessitent `@login_required` + `@admin_required`.

| Methode | URL | Description |
|---------|-----|-------------|
| GET | `/admin/dashboard-stats` | Statistiques admin |
| GET | `/admin/system-metrics` | Metriques systeme |
| GET | `/admin/database-metrics` | Metriques BDD |
| GET | `/admin/active-sessions` | Sessions actives |
| GET | `/admin/system-logs` | Logs systeme |
| GET | `/admin/alerts` | Alertes systeme |
| GET | `/admin/monitoring-summary` | Resume monitoring |
| GET | `/admin/users` | Liste utilisateurs |
| GET | `/admin/users/<id>/activity` | Activite recente (connexions, transactions, notifications). Param `limit` (max 50) |
| GET | `/admin/users/<id>/accounts` | Comptes d'un utilisateur (donnees minimisees, sans IBAN/numero) |
| GET | `/admin/users/<id>/transactions` | Transactions paginees. Params `page`, `per_page` (max 100) |
| POST | `/admin/users/<id>/toggle` | Activer/desactiver un utilisateur |
| POST | `/admin/users/<id>/reset-2fa` | Reset 2FA d'un utilisateur |
| POST | `/admin/users/<id>/reset-password` | Reset mot de passe |

---

## 14. Utilisateurs (`/api/v1/users`)

Authentification JWT requise. Permissions verifiees.

| Methode | URL | Description |
|---------|-----|-------------|
| PUT | `/users/<id>/profile` | Modifier le profil |
| GET | `/users/<id>/roles` | Roles d'un utilisateur |
| POST | `/users/<id>/roles/<role_id>` | Ajouter un role |
| DELETE | `/users/<id>/roles/<role_id>` | Retirer un role |
| PUT | `/users/<id>` | Modifier un utilisateur |
| DELETE | `/users/<id>` | Supprimer (desactiver) |

---

## Resume

| Module | Routes | Auth |
|--------|--------|------|
| Auth | 8 | JWT / public |
| Comptes | 7 | Session |
| Categories | 5 | Session |
| Transactions | 8 | Session |
| Budgets | 10 | Session |
| Dashboard | 8 | Session |
| Rapports | 7 | Session |
| Recurring | 6 | Session |
| Profil | 11 | Session |
| Parametres | 8 | Session |
| Notifications | 4 | Session |
| Appareils | 5 | Session |
| Admin | 14 | Session + Admin |
| Utilisateurs | 6 | JWT |
| **Total** | **107** | |
