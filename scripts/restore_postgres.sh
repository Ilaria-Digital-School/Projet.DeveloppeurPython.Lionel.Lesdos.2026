#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Restauration PostgreSQL — Appli Budget
#
# Restaure une sauvegarde de backup_postgres.sh.
#
# Usage :
#   ./restore_postgres.sh <fichier.sql.gz>
#       Restaure dans la base 'budget_restore' (la base de l'appli n'est pas
#       touchee) : pour consulter ou recuperer des donnees.
#
#   ./restore_postgres.sh <fichier.sql.gz> --remplacer
#       REMPLACE la base de l'appli. Arrete l'appli, sauvegarde l'etat actuel
#       (filet de securite), recree la base, restaure, puis relance l'appli.
#       Demande de taper le nom de la base pour confirmer.
#
# Variables surchargeables : COMPOSE_DIR, BACKUP_DIR, COMPOSE,
# DB_NAME / DB_USER (par defaut : POSTGRES_DB / POSTGRES_USER du .env)
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-/var/www/Appli_Web_Budget}"
BACKUP_DIR="${BACKUP_DIR:-/opt/backup/dumps}"
COMPOSE="${COMPOSE:-docker compose --project-directory ${COMPOSE_DIR}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERREUR] $*" >&2; exit 1; }

FICHIER="${1:-}"
MODE="${2:-}"
[[ -n "${FICHIER}" ]] || die "usage : $0 <fichier.sql.gz> [--remplacer]"
[[ -f "${FICHIER}" ]] || die "fichier introuvable : ${FICHIER}"
gzip -t "${FICHIER}" || die "archive gzip corrompue : ${FICHIER}"
zcat "${FICHIER}" | tail -n 5 | grep -q "PostgreSQL database dump complete" \
    || die "dump incomplet (marqueur de fin absent) : ${FICHIER}"

ENV_FILE="${COMPOSE_DIR}/.env"
if [[ -z "${DB_NAME:-}" && -f "${ENV_FILE}" ]]; then
    DB_NAME="$(grep -m1 '^POSTGRES_DB=' "${ENV_FILE}" | cut -d'=' -f2- | tr -d '"'"'"'')"
fi
if [[ -z "${DB_USER:-}" && -f "${ENV_FILE}" ]]; then
    DB_USER="$(grep -m1 '^POSTGRES_USER=' "${ENV_FILE}" | cut -d'=' -f2- | tr -d '"'"'"'')"
fi
DB_NAME="${DB_NAME:-budget}"
DB_USER="${DB_USER:-budget_user}"

${COMPOSE} ps --status running db | grep -q db || die "le conteneur PostgreSQL 'db' ne tourne pas"
psql_admin() { ${COMPOSE} exec -T db psql -U "${DB_USER}" -d postgres -v ON_ERROR_STOP=1 -q "$@"; }

restaurer_dans() {
    local cible="$1"
    psql_admin -c "DROP DATABASE IF EXISTS ${cible}" -c "CREATE DATABASE ${cible}"
    zcat "${FICHIER}" | ${COMPOSE} exec -T db psql -U "${DB_USER}" -d "${cible}" -q -v ON_ERROR_STOP=1 >/dev/null
    log "Restaure dans '${cible}' : $(${COMPOSE} exec -T db psql -U "${DB_USER}" -d "${cible}" -Atc \
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'") tables"
}

if [[ "${MODE}" != "--remplacer" ]]; then
    restaurer_dans "budget_restore"
    log "La base de l'appli '${DB_NAME}' n'a pas ete modifiee."
    log "Consulter : ${COMPOSE} exec db psql -U ${DB_USER} -d budget_restore"
    exit 0
fi

# ── Remplacement de la base de l'appli ────────────────────────────
echo "ATTENTION : la base '${DB_NAME}' va etre REMPLACEE par ${FICHIER}."
read -r -p "Tapez le nom de la base pour confirmer : " CONFIRMATION
[[ "${CONFIRMATION}" == "${DB_NAME}" ]] || die "confirmation incorrecte, rien n'a ete modifie"

log "Filet de securite : sauvegarde de l'etat actuel..."
BACKUP_DIR="${BACKUP_DIR}" COMPOSE_DIR="${COMPOSE_DIR}" COMPOSE="${COMPOSE}" \
    "${SCRIPT_DIR}/backup_postgres.sh" || die "sauvegarde prealable impossible, restauration annulee"

log "Arret de l'appli et du scheduler..."
${COMPOSE} stop app scheduler
# Relancer l'appli quoi qu'il arrive (meme si la restauration echoue)
trap 'log "Relance de l'"'"'appli..."; ${COMPOSE} start app scheduler' EXIT

# Restauration dans une base temporaire, puis echange : la base de l'appli
# n'est remplacee que si la restauration a reussi
restaurer_dans "${DB_NAME}_restore_tmp"
psql_admin -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid()" >/dev/null
psql_admin -c "DROP DATABASE ${DB_NAME}" -c "ALTER DATABASE ${DB_NAME}_restore_tmp RENAME TO ${DB_NAME}"
log "Base '${DB_NAME}' remplacee."

log "Termine (au redemarrage, l'appli applique les migrations si la sauvegarde est plus ancienne)."
