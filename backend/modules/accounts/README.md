# Module de Gestion des Comptes

Ce module gère les opérations liées aux comptes bancaires, y compris la création, la mise à jour, la suppression et les transferts entre comptes.

## Améliorations Récentes

### 1. Standardisation des Imports
- Utilisation d'imports absolus depuis le package racine
- Suppression des imports circulaires
- Organisation claire des dépendances

### 2. Gestion des Transactions Concurrentes
- Implémentation du verrouillage optimiste
- Gestion des conflits avec réessai automatique
- Isolation des transactions pour garantir l'intégrité des données

### 3. Amélioration des Tests
- Couverture accrue des cas de test
- Tests de concurrence pour les opérations sensibles
- Vérification des contraintes d'intégrité

### 4. Documentation
- Documentation complète des méthodes et classes
- Exemples d'utilisation
- Gestion des erreurs documentée

## Utilisation

```python
# Création d'un compte
account_data = {
    "user_id": 1,
    "name": "Compte Courant",
    "account_type": "courant",
    "balance": 1000.00,
    "currency": "EUR"
}
account = AccountService.create_account(1, account_data)

# Transfert entre comptes
transfer_data = {
    "amount": 100.00,
    "currency": "EUR",
    "description": "Virement mensuel"
}
result = AccountService.transfer_between_accounts(
    source_account_id=1,
    target_account_id=2,
    user_id=1,
    transfer_data=transfer_data
)
```

## Tests

Pour exécuter les tests :

```bash
# Tous les tests
pytest tests/

# Tests unitaires uniquement
pytest tests/unit/test_services/test_account_services.py

# Avec couverture de code
pytest --cov=backend.core.services.accounts tests/unit/test_services/test_account_services.py
```
