# Compte de Demonstration

## Identifiants

| Champ         | Valeur            |
|---------------|-------------------|
| **Email**     | `demo@budget.fr`  |
| **Mot de passe** | `DemoBudget2026!` |
| **Role**      | Utilisateur       |
| **2FA**       | Desactivee        |

## Donnees pre-chargees

### Comptes bancaires (3)

| Compte          | Type          | Solde         |
|-----------------|---------------|---------------|
| Compte Courant  | Courant       | 2 450,75 EUR  |
| Livret A        | Epargne       | 8 200,00 EUR  |
| Carte Credit    | Carte credit  | -342,50 EUR   |

### Categories (12)

**Depenses (8)** : Alimentation, Transport, Logement, Loisirs, Sante, Shopping, Factures, Education

**Revenus (4)** : Salaire, Freelance, Remboursement, Autres revenus

### Budgets mensuels (6)

| Budget       | Montant   |
|--------------|-----------|
| Alimentation | 400 EUR   |
| Transport    | 200 EUR   |
| Loisirs      | 150 EUR   |
| Shopping     | 200 EUR   |
| Factures     | 300 EUR   |
| Sante        | 100 EUR   |

### Transactions (131)

- **Periode** : 90 derniers jours (mi-fevrier a mi-mai 2026)
- **Types** : depenses quotidiennes (courses, transport, loisirs, factures) et revenus (salaire mensuel, freelance, remboursements)
- **Repartition** : ~80% depenses, ~20% revenus
- **Exemples** : Carrefour, SNCF TGV, Netflix, Loyer mensuel, Salaire mensuel, EDF electricite

## Fonctionnalites a presenter

Une fois connecte avec le compte demo, les pages suivantes contiennent des donnees :

1. **Dashboard** (`/dashboard/`) : graphiques de repartition des depenses, tendances mensuelles, soldes des comptes
2. **Comptes** (`/comptes/`) : liste des 3 comptes avec soldes
3. **Transactions** (`/transactions/`) : historique des 131 transactions avec filtres par compte, categorie, type et periode
4. **Categories** (`/categories/`) : 12 categories personnalisees avec codes couleur
5. **Budgets** (`/budgets/`) : 6 budgets mensuels avec suivi de progression
6. **Rapports** (`/reports/`) : generation de rapports PDF et export CSV/Excel

## Recréer le compte demo

Si le compte demo doit etre reinitialise :

```bash
# Depuis le serveur VPS
docker cp backend/scripts/create_demo_user.py budget-app:/tmp/create_demo_user.py
docker exec budget-app bash -c "cd /app/backend && python3 /tmp/create_demo_user.py"
```

Le script verifie si l'utilisateur existe deja avant de le creer.
