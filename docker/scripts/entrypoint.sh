#!/bin/bash
set -e

echo "=== Budget App - Entrypoint ==="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! python3 -c "import socket; s=socket.socket(); s.connect(('db',5432)); s.close()" 2>/dev/null; do
    echo "  PostgreSQL not ready, retrying in 2s..."
    sleep 2
done
echo "PostgreSQL is ready!"

# Initialize or migrate database
cd /app/backend
export FLASK_APP="app:create_app('production')"

echo "Running database migrations..."
flask db upgrade
echo "Database migrations complete."

# Seed default categories (idempotent, runs once before workers start)
echo "Seeding default categories..."
python3 - <<'PYEOF'
from app import create_app
from core.services.categories.category_services import CategoryService

app = create_app("production")
with app.app_context():
    CategoryService.ensure_default_categories_exist()
print("Default categories ensured.")
PYEOF

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn \
    "app:create_app('production')" \
    --bind 0.0.0.0:5000 \
    --workers "${WORKERS:-4}" \
    --threads "${THREADS:-2}" \
    --timeout "${TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile - \
    --log-level info
