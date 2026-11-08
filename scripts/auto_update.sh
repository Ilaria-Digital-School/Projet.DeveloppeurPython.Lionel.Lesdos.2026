#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Mise a jour automatique securisee — Appli Budget
#
# Met a jour les images Docker, packages Python (patch/minor),
# packages npm (patch/minor), avec backup prealable et rollback.
#
# Usage:  sudo /opt/scripts/auto_update.sh
# Log:    /var/log/auto_update.log
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────
PROJECT_DIR="/var/www/Appli_Web_Budget"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
BACKUP_SCRIPT="${PROJECT_DIR}/scripts/backup_postgres.sh"
LOG_FILE="/var/log/auto_update.log"
HEALTH_URL="https://example.com/"
HEALTH_RETRIES=12
HEALTH_DELAY=5

# Packages Python a ne jamais mettre a jour automatiquement
# pydantic/pydantic_core : couplage strict, doivent etre mis a jour ensemble manuellement
BLACKLIST="marshmallow redis reportlab cryptography matplotlib pydantic pydantic_core pydantic-core"

# Compteurs pour le rapport final
UPDATED_DOCKER=()
UPDATED_PIP=()
UPDATED_NPM=false
HAD_ERRORS=false

# ── Fonctions utilitaires ────────────────────────────────────────

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "${msg}" | tee -a "${LOG_FILE}"
}

die() {
    log "ERREUR FATALE: $*"
    log "=== Arret du script ==="
    exit 1
}

# Compare deux versions semver. Retourne :
#   0 si meme majeure (patch/minor safe)
#   1 si majeure differente (breaking)
is_major_bump() {
    local current="$1" available="$2"
    # Extraire la majeure (premier nombre avant le premier point)
    local cur_major="${current%%.*}"
    local avail_major="${available%%.*}"
    [[ "${cur_major}" != "${avail_major}" ]]
}

is_blacklisted() {
    local pkg="$1"
    local bl
    # Normaliser : minuscules, tirets et underscores equivalents
    local pkg_norm="${pkg,,}"
    pkg_norm="${pkg_norm//-/_}"
    for bl in ${BLACKLIST}; do
        local bl_norm="${bl,,}"
        bl_norm="${bl_norm//-/_}"
        if [[ "${pkg_norm}" == "${bl_norm}" ]]; then
            return 0
        fi
    done
    return 1
}

health_check() {
    local attempt
    for attempt in $(seq 1 "${HEALTH_RETRIES}"); do
        if curl -fsSL -o /dev/null -w '' --max-time 10 "${HEALTH_URL}" 2>/dev/null; then
            log "Health check OK (tentative ${attempt}/${HEALTH_RETRIES})"
            return 0
        fi
        log "Health check echoue (tentative ${attempt}/${HEALTH_RETRIES}), attente ${HEALTH_DELAY}s..."
        sleep "${HEALTH_DELAY}"
    done
    return 1
}

rollback_git() {
    log "!!! ROLLBACK : restauration du dernier commit stable"
    cd "${PROJECT_DIR}"
    git checkout -- backend/requirements.txt frontend/package.json frontend/package-lock.json frontend/static/css/tailwind.css 2>/dev/null || true
    docker compose -f "${COMPOSE_FILE}" up --build -d app scheduler
    HAD_ERRORS=true
}

# ── Debut ─────────────────────────────────────────────────────────

log "================================================================"
log "=== Debut mise a jour automatique ==="
log "================================================================"

# Verifier qu'on est root (necessaire pour docker et logs)
if [[ "${EUID}" -ne 0 ]]; then
    die "Ce script doit etre execute en tant que root (sudo)"
fi

# ── Etape 1 : Backup PostgreSQL ──────────────────────────────────

log "--- Etape 1/6 : Backup PostgreSQL ---"

if [[ ! -x "${BACKUP_SCRIPT}" ]]; then
    die "Script de backup introuvable ou non executable : ${BACKUP_SCRIPT}"
fi

if ! "${BACKUP_SCRIPT}" >> "${LOG_FILE}" 2>&1; then
    die "Backup PostgreSQL echoue — aucune modification ne sera effectuee"
fi

log "Backup PostgreSQL termine avec succes"

# ── Etape 2 : Mise a jour images Docker ──────────────────────────

log "--- Etape 2/6 : Mise a jour images Docker ---"

# Sauvegarder les IDs d'images actuels pour comparer
DB_IMAGE_BEFORE=$(docker inspect --format '{{.Image}}' appli_web_budget-db-1 2>/dev/null || echo "none")
REDIS_IMAGE_BEFORE=$(docker inspect --format '{{.Image}}' appli_web_budget-redis-1 2>/dev/null || echo "none")
NGINX_IMAGE_BEFORE=$(docker inspect --format '{{.Image}}' reverse-proxy-nginx 2>/dev/null || echo "none")

# Pull les nouvelles images
log "Pull des images Docker..."
docker compose -f "${COMPOSE_FILE}" pull db redis 2>&1 | tee -a "${LOG_FILE}"
docker pull nginx:stable-alpine 2>&1 | tee -a "${LOG_FILE}"

# Verifier si les images ont change pour db et redis
DB_IMAGE_AFTER=$(docker image inspect --format '{{.Id}}' postgres:18-alpine 2>/dev/null || echo "none")
REDIS_IMAGE_AFTER=$(docker image inspect --format '{{.Id}}' redis:8-alpine 2>/dev/null || echo "none")
NGINX_IMAGE_AFTER=$(docker image inspect --format '{{.Id}}' nginx:stable-alpine 2>/dev/null || echo "none")

if [[ "${DB_IMAGE_BEFORE}" != "${DB_IMAGE_AFTER}" ]]; then
    log "Image postgres:18-alpine mise a jour, redemarrage du conteneur db..."
    docker compose -f "${COMPOSE_FILE}" up -d db
    UPDATED_DOCKER+=("postgres:18-alpine")
    # Attendre que la DB soit healthy avant de continuer
    log "Attente que PostgreSQL soit healthy..."
    sleep 5
    for i in $(seq 1 12); do
        if docker compose -f "${COMPOSE_FILE}" ps db | grep -q "healthy"; then
            break
        fi
        sleep 5
    done
fi

if [[ "${REDIS_IMAGE_BEFORE}" != "${REDIS_IMAGE_AFTER}" ]]; then
    log "Image redis:8-alpine mise a jour, redemarrage du conteneur redis..."
    docker compose -f "${COMPOSE_FILE}" up -d redis
    UPDATED_DOCKER+=("redis:8-alpine")
fi

if [[ "${NGINX_IMAGE_BEFORE}" != "${NGINX_IMAGE_AFTER}" ]]; then
    log "Image nginx:stable-alpine mise a jour, recreation du conteneur nginx..."
    # Nginx est gere hors docker-compose, il faut le recreer manuellement
    docker stop reverse-proxy-nginx 2>/dev/null || true
    docker rm reverse-proxy-nginx 2>/dev/null || true
    docker run -d \
        --name reverse-proxy-nginx \
        --restart unless-stopped \
        --network proxy_network \
        --network-alias nginx \
        -p 80:80 \
        -p 443:443 \
        -v /opt/reverse-proxy/conf.d:/etc/nginx/conf.d:ro \
        -v reverse-proxy_certbot_certs:/etc/letsencrypt:ro \
        -v reverse-proxy_certbot_www:/var/www/certbot:ro \
        -v /var/www/Appli_Web_Budget/frontend/static:/var/www/static:ro \
        -v /opt/reverse-proxy/logs:/var/log/nginx:rw \
        nginx:stable-alpine
    UPDATED_DOCKER+=("nginx:stable-alpine")
fi

if [[ ${#UPDATED_DOCKER[@]} -eq 0 ]]; then
    log "Aucune image Docker a mettre a jour"
else
    log "Images Docker mises a jour : ${UPDATED_DOCKER[*]}"
fi

# ── Etape 3 : Mise a jour packages Python ────────────────────────

log "--- Etape 3/6 : Mise a jour packages Python ---"

# Obtenir la liste des packages obsoletes depuis le conteneur app
OUTDATED_JSON=$(docker exec budget-app pip list --outdated --format=json 2>/dev/null || echo "[]")

if [[ "${OUTDATED_JSON}" == "[]" || -z "${OUTDATED_JSON}" ]]; then
    log "Aucun package Python obsolete"
else
    REQUIREMENTS_FILE="${PROJECT_DIR}/backend/requirements.txt"
    CHANGES_MADE=false

    # Parser le JSON et traiter chaque package
    while IFS= read -r line; do
        pkg_name=$(echo "${line}" | cut -d'|' -f1)
        current_ver=$(echo "${line}" | cut -d'|' -f2)
        latest_ver=$(echo "${line}" | cut -d'|' -f3)

        # Ignorer les packages blacklistes
        if is_blacklisted "${pkg_name}"; then
            log "  SKIP (blacklist) : ${pkg_name} ${current_ver} -> ${latest_ver}"
            continue
        fi

        # Ignorer les mises a jour majeures
        if is_major_bump "${current_ver}" "${latest_ver}"; then
            log "  SKIP (majeure)   : ${pkg_name} ${current_ver} -> ${latest_ver}"
            continue
        fi

        log "  MAJ : ${pkg_name} ${current_ver} -> ${latest_ver}"
        UPDATED_PIP+=("${pkg_name}: ${current_ver} -> ${latest_ver}")

        # Mettre a jour requirements.txt (insensible a la casse pour le nom du package)
        # On cherche la ligne exacte avec == et on remplace la version
        if grep -qi "^${pkg_name}==" "${REQUIREMENTS_FILE}"; then
            sed -i "s/^${pkg_name}==.*$/${pkg_name}==${latest_ver}/i" "${REQUIREMENTS_FILE}"
            CHANGES_MADE=true
        fi

    done < <(echo "${OUTDATED_JSON}" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for pkg in data:
    print(f\"{pkg['name']}|{pkg['version']}|{pkg['latest_version']}\")
" 2>/dev/null || true)

    if [[ "${CHANGES_MADE}" == true ]]; then
        # Dry-run : verifier que pip peut resoudre les dependances avant de rebuild
        log "Verification de la resolution des dependances (dry-run)..."
        if ! docker run --rm -v "${REQUIREMENTS_FILE}:/tmp/requirements.txt:ro" \
            python:3.14-slim pip install --dry-run --no-cache-dir -r /tmp/requirements.txt 2>&1 | tee -a "${LOG_FILE}"; then
            log "!!! Conflit de dependances detecte — annulation des modifications Python"
            cd "${PROJECT_DIR}"
            git checkout -- backend/requirements.txt
            UPDATED_PIP=()
            HAD_ERRORS=true
        else
            log "Resolution OK, rebuild de l'application..."
            cd "${PROJECT_DIR}"
            docker compose -f "${COMPOSE_FILE}" up --build -d app scheduler 2>&1 | tee -a "${LOG_FILE}"

            log "Verification health check apres mise a jour Python..."
            sleep 10
            if ! health_check; then
                log "!!! Health check echoue apres mise a jour Python"
                rollback_git
                log "Rollback termine, rebuild en cours..."
                docker compose -f "${COMPOSE_FILE}" up --build -d app scheduler 2>&1 | tee -a "${LOG_FILE}"
                sleep 10
                if health_check; then
                    log "Application restauree avec succes apres rollback"
                else
                    die "Application toujours en erreur apres rollback — intervention manuelle requise"
                fi
            fi
        fi
    else
        log "Aucune mise a jour Python applicable"
    fi
fi

# ── Etape 4 : Mise a jour packages npm ───────────────────────────

log "--- Etape 4/6 : Mise a jour packages npm ---"

FRONTEND_DIR="${PROJECT_DIR}/frontend"
cd "${FRONTEND_DIR}"

# Sauvegarder le hash du lockfile avant
LOCK_HASH_BEFORE=""
if [[ -f "package-lock.json" ]]; then
    LOCK_HASH_BEFORE=$(md5sum package-lock.json | cut -d' ' -f1)
fi

# npm update respecte les ranges semver de package.json (^/~)
# donc ne fera jamais de mise a jour majeure
npm update --save 2>&1 | tee -a "${LOG_FILE}" || true

LOCK_HASH_AFTER=""
if [[ -f "package-lock.json" ]]; then
    LOCK_HASH_AFTER=$(md5sum package-lock.json | cut -d' ' -f1)
fi

if [[ "${LOCK_HASH_BEFORE}" != "${LOCK_HASH_AFTER}" ]]; then
    log "Packages npm mis a jour, rebuild CSS Tailwind..."
    npm run build:css 2>&1 | tee -a "${LOG_FILE}"
    UPDATED_NPM=true
    log "Build CSS termine"

    # Health check apres npm
    log "Verification health check apres mise a jour npm..."
    if ! health_check; then
        log "!!! Health check echoue apres mise a jour npm"
        rollback_git
        log "Rollback npm termine"
    fi
else
    log "Aucun package npm a mettre a jour"
fi

# ── Etape 5 : Nettoyage ──────────────────────────────────────────

log "--- Etape 5/6 : Nettoyage images Docker orphelines ---"

PRUNED=$(docker image prune -f 2>&1)
log "${PRUNED}"

# ── Etape 6 : Rapport final ──────────────────────────────────────

log "--- Etape 6/6 : Rapport final ---"
log ""
log "==============================="
log "  RESUME DES MISES A JOUR"
log "==============================="

if [[ ${#UPDATED_DOCKER[@]} -gt 0 ]]; then
    log "Images Docker :"
    for img in "${UPDATED_DOCKER[@]}"; do
        log "  - ${img}"
    done
else
    log "Images Docker : aucune mise a jour"
fi

if [[ ${#UPDATED_PIP[@]} -gt 0 ]]; then
    log "Packages Python :"
    for pkg in "${UPDATED_PIP[@]}"; do
        log "  - ${pkg}"
    done
else
    log "Packages Python : aucune mise a jour"
fi

if [[ "${UPDATED_NPM}" == true ]]; then
    log "Packages npm : mis a jour (voir details ci-dessus)"
else
    log "Packages npm : aucune mise a jour"
fi

if [[ "${HAD_ERRORS}" == true ]]; then
    log ""
    log "⚠ ATTENTION : Des rollbacks ont eu lieu, verifier les details ci-dessus"
fi

log ""
log "================================================================"
log "=== Fin mise a jour automatique ==="
log "================================================================"
