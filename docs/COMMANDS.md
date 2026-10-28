# Commandes de gestion de l'application

## Commandes Flask CLI

### Initialisation

```bash
# Initialiser la base de donnees (creation des tables)
cd backend
flask init-db

# Appliquer les migrations Alembic
flask db upgrade

# Creer une nouvelle migration apres modification des modeles
flask db migrate -m "Description des changements"
```

### Administration

```bash
# Creer un utilisateur administrateur
flask create-admin

# Generer des donnees de test
flask create-test-data

# Nettoyer les donnees obsoletes
flask cleanup-data
```

### Controle des soldes

```bash
# Verifie que chaque solde = solde initial + effet des transactions
flask accounts check-balances
# Ramene les soldes incoherents a leur valeur attendue
flask accounts check-balances --fix
```

En production (dans le conteneur, FLASK_APP n'est defini que par l'entrypoint) :

```bash
docker compose exec -w /app/backend -e FLASK_APP="app:create_app('production')" \
    app flask accounts check-balances
```

### Suppression des comptes

`DELETE /api/v1/settings/account` desactive le compte et planifie sa purge a
J+7 ; se reconnecter avant annule la suppression. Le scheduler lance la purge
chaque jour (`docker/scripts/scheduler.sh`) ; pour la lancer a la main :

```bash
flask accounts purge-deleted   # supprime definitivement les comptes echus
```

### Workers et notifications

```bash
# Demarrer un worker RQ (necessite Redis)
flask worker start

# Relancer les notifications en echec
flask notifications retry-failed
```

## Scripts utilitaires

Les scripts se trouvent dans `backend/scripts/` :

```bash
# Initialiser la base de donnees avec les donnees de base
python scripts/init_db.py

# Initialiser les donnees (categories par defaut, roles, etc.)
python scripts/init_data.py

# Creer un utilisateur de demonstration (necessite la variable d'env DEMO_PASSWORD)
python scripts/create_demo_user.py

# Reinitialiser le mot de passe administrateur
python scripts/reset_admin_password.py

# Verifier l'etat de la base de donnees
python scripts/check_db.py

# Maintenance de la base de donnees (donnees de demonstration)
python scripts/db_maintenance/create_demo_data.py
python scripts/db_maintenance/cleanup_demo_data.py
```

## Demarrage de l'application

### Mode developpement

```bash
cd backend

# Demarrer avec Flask en mode debug (port 8080)
flask run --debug --port 8080

# Ou via les scripts fournis
./scripts/start.sh          # Demarrer l'application (trouve un port libre)
./scripts/stop.sh           # Arreter l'application (-f pour forcer)
```

L'application est accessible sur http://localhost:8080

### Mode production (Docker)

```bash
# Construire et demarrer les conteneurs
docker compose up --build -d

# Arreter les conteneurs
docker compose down

# Voir les logs
docker compose logs -f
```

L'application est deployee sur https://example.com

## Tests

```bash
cd backend

# Lancer tous les tests (185 tests)
python3 -m pytest --tb=short -q

# Tests avec couverture de code
pytest --cov=. tests/

# Tests unitaires uniquement
pytest tests/unit/

# Tests d'integration uniquement
pytest tests/integration/

# Tests fonctionnels uniquement
pytest tests/functional/
```

## Voir les logs

```bash
# Logs de l'application
tail -f backend/logs/app.log
```

## Sauvegardes de la base (production)

Scripts dans `scripts/`, a lancer sur le serveur (ils utilisent `docker compose`).

```bash
# Sauvegarde : dump compresse, valide (gzip intact + dump complet) puis range
#   /opt/backup/dumps/daily/    une par execution, conservee 14 jours
#   /opt/backup/dumps/monthly/  la premiere de chaque mois, conservee 12 mois
scripts/backup_postgres.sh
scripts/backup_postgres.sh --verify   # + restauration test dans une base jetable

# Restauration dans la base 'budget_restore' (la base de l'appli n'est pas touchee)
scripts/restore_postgres.sh /opt/backup/dumps/daily/budget_AAAAMMJJ_HHMMSS.sql.gz

# Remplacement de la base de l'appli (confirmation demandee, sauvegarde de
# l'etat actuel avant, appli arretee puis relancee)
scripts/restore_postgres.sh /opt/backup/dumps/daily/budget_AAAAMMJJ_HHMMSS.sql.gz --remplacer
```

Planification (`sudo crontab -e`) : tous les jours a 2h, avec test de
restauration le dimanche.

```cron
0 2 * * 1-6 /var/www/Appli_Web_Budget/scripts/backup_postgres.sh >> /var/log/backup_postgres.log 2>&1
0 2 * * 0   /var/www/Appli_Web_Budget/scripts/backup_postgres.sh --verify >> /var/log/backup_postgres.log 2>&1
```

Copie hors serveur : definir `BACKUP_REMOTE` (destination rsync, ex.
`BACKUP_REMOTE=user@hote:/sauvegardes/budget`) devant la commande du cron.
Variables surchargeables : `BACKUP_DIR`, `COMPOSE_DIR`, `RETENTION_DAYS`,
`RETENTION_MONTHS`, `DB_NAME`, `DB_USER`.

## Supervision

- `GET /healthz` (public, sans detail) : `{"status": "ok"}` si l'app et la base
  repondent, `503` sinon.
- Healthchecks Docker (`docker-compose.yml`) : `app` interroge `/healthz` toutes
  les 30 s ; `scheduler` est sain si un passage a reussi depuis moins de 25 h
  (`/tmp/scheduler_heartbeat`). `docker compose ps` affiche `healthy` /
  `unhealthy`. Docker ne redemarre pas un conteneur `unhealthy` de lui-meme.
