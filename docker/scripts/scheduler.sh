#!/bin/bash
set -e

echo "=== Budget App - Scheduler ==="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! python3 -c "import socket; s=socket.socket(); s.connect(('db',5432)); s.close()" 2>/dev/null; do
    echo "  PostgreSQL not ready, retrying in 2s..."
    sleep 2
done
echo "PostgreSQL is ready!"

cd /app/backend
export FLASK_APP="app:create_app('production')"

INTERVAL="${SCHEDULER_INTERVAL:-86400}"
RETRY_DELAY="${SCHEDULER_RETRY_DELAY:-300}"
MAX_RETRIES=3

# Les migrations sont appliquees par le conteneur app (entrypoint.sh), qui
# demarre en meme temps : sans attendre, le premier passage tournait sur un
# schema pas encore a jour apres chaque deploiement et echouait.
echo "Waiting for database migrations (applied by the app container)..."
for _ in $(seq 1 120); do
    if flask db current 2>/dev/null | grep -q "(head)"; then
        echo "Database schema is up to date."
        break
    fi
    sleep 5
done

echo "Scheduler started (interval: ${INTERVAL}s)"

retries=0
while true; do
    echo "[$(date -Iseconds)] Processing recurring transactions..."
    if flask recurring process; then
        retries=0
        delay="$INTERVAL"
        # Battement de cœur pour le healthcheck Docker (docker-compose.yml)
        date +%s > /tmp/scheduler_heartbeat
    else
        retries=$((retries + 1))
        echo "[$(date -Iseconds)] ERROR: recurring process failed (attempt ${retries})"
        # Reessayer rapidement quelques fois avant d'attendre le passage suivant
        if [ "$retries" -le "$MAX_RETRIES" ]; then
            delay="$RETRY_DELAY"
        else
            retries=0
            delay="$INTERVAL"
        fi
    fi
    # Purge des comptes dont la suppression demandee est echue (J+7)
    flask accounts purge-deleted || echo "[$(date -Iseconds)] ERROR: account purge failed"
    echo "[$(date -Iseconds)] Done. Sleeping ${delay}s..."
    sleep "$delay"
done
