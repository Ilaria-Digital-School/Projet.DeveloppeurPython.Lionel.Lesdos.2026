#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────
# Sauvegarde PostgreSQL — Appli Budget
#
# Dump de la base du conteneur Docker 'db', compresse, valide puis range :
#   - daily/   : une sauvegarde par execution, conservee RETENTION_DAYS jours
#   - monthly/ : la premiere sauvegarde de chaque mois, conservee
#                RETENTION_MONTHS mois
# Une sauvegarde n'est rangee qu'apres validation (gzip intact + marqueur de fin
# de pg_dump) : un dump interrompu ne remplace jamais une bonne sauvegarde.
# Option --verify : restaure la sauvegarde dans une base jetable et compte les
# tables, pour s'assurer qu'elle est reellement restaurable.
#
# Usage :
#   ./backup_postgres.sh            # sauvegarde + rotation
#   ./backup_postgres.sh --verify   # idem + test de restauration
#
# Cron (tous les jours a 2h, test de restauration le dimanche) :
#   0 2 * * 1-6 /var/www/Appli_Web_Budget/scripts/backup_postgres.sh >> /var/log/backup_postgres.log 2>&1
#   0 2 * * 0   /var/www/Appli_Web_Budget/scripts/backup_postgres.sh --verify >> /var/log/backup_postgres.log 2>&1
#
# Variables surchargeables : BACKUP_DIR, COMPOSE_DIR, RETENTION_DAYS,
# RETENTION_MONTHS, COMPOSE (commande docker compose complete), DB_NAME / DB_USER
# (par defaut : POSTGRES_DB / POSTGRES_USER du .env),
# BACKUP_REMOTE (destination rsync hors serveur, ex. user@hote:/sauvegardes/budget)
# ──────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/opt/backup/dumps}"
COMPOSE_DIR="${COMPOSE_DIR:-/var/www/Appli_Web_Budget}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
RETENTION_MONTHS="${RETENTION_MONTHS:-12}"
COMPOSE="${COMPOSE:-docker compose --project-directory ${COMPOSE_DIR}}"
BACKUP_REMOTE="${BACKUP_REMOTE:-}"
VERIFY=false
[[ "${1:-}" == "--verify" ]] && VERIFY=true

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
die() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERREUR] $*" >&2; exit 1; }

# Identifiants (seulement les variables POSTGRES_* du .env)
ENV_FILE="${COMPOSE_DIR}/.env"
if [[ -z "${DB_NAME:-}" && -f "${ENV_FILE}" ]]; then
    DB_NAME="$(grep -m1 '^POSTGRES_DB=' "${ENV_FILE}" | cut -d'=' -f2- | tr -d '"'"'"'')"
fi
if [[ -z "${DB_USER:-}" && -f "${ENV_FILE}" ]]; then
    DB_USER="$(grep -m1 '^POSTGRES_USER=' "${ENV_FILE}" | cut -d'=' -f2- | tr -d '"'"'"'')"
fi
DB_NAME="${DB_NAME:-budget}"
DB_USER="${DB_USER:-budget_user}"

# ── Verifications ─────────────────────────────────────────────────
command -v docker &>/dev/null || die "docker n'est pas installe ou pas dans le PATH"
${COMPOSE} ps --status running db | grep -q db || die "le conteneur PostgreSQL 'db' ne tourne pas"

mkdir -p "${BACKUP_DIR}/daily" "${BACKUP_DIR}/monthly"
chmod 700 "${BACKUP_DIR}"

# ── Dump ──────────────────────────────────────────────────────────
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
FINAL="${BACKUP_DIR}/daily/budget_${TIMESTAMP}.sql.gz"
TMP="${BACKUP_DIR}/.budget_${TIMESTAMP}.sql.gz.partial"
trap 'rm -f "${TMP}"' EXIT

log "Sauvegarde de la base '${DB_NAME}'..."
${COMPOSE} exec -T db pg_dump -U "${DB_USER}" -d "${DB_NAME}" --no-owner --no-acl \
    | gzip > "${TMP}" \
    || die "pg_dump a echoue, sauvegarde abandonnee"

# ── Validation : archive intacte et dump complet ──────────────────
gzip -t "${TMP}" || die "archive gzip corrompue"
zcat "${TMP}" | tail -n 5 | grep -q "PostgreSQL database dump complete" \
    || die "dump incomplet (marqueur de fin absent)"

chmod 600 "${TMP}"
mv "${TMP}" "${FINAL}"
log "Sauvegarde validee : ${FINAL} ($(du -h "${FINAL}" | cut -f1))"

# Premiere sauvegarde du mois : copie dans monthly/
MOIS="$(date +%Y%m)"
if ! compgen -G "${BACKUP_DIR}/monthly/budget_${MOIS}*.sql.gz" >/dev/null; then
    cp -p "${FINAL}" "${BACKUP_DIR}/monthly/"
    log "Copie mensuelle : monthly/$(basename "${FINAL}")"
fi

# ── Test de restauration (--verify) ───────────────────────────────
if ${VERIFY}; then
    VERIFY_DB="budget_restore_check"
    log "Test de restauration dans la base jetable '${VERIFY_DB}'..."
    ${COMPOSE} exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -qc "DROP DATABASE IF EXISTS ${VERIFY_DB}" \
        -c "CREATE DATABASE ${VERIFY_DB}" >/dev/null
    zcat "${FINAL}" | ${COMPOSE} exec -T db psql -U "${DB_USER}" -d "${VERIFY_DB}" -q -v ON_ERROR_STOP=1 >/dev/null \
        || die "la restauration de ${FINAL} a echoue"
    compter='SELECT count(*) FROM information_schema.tables WHERE table_schema = '"'"'public'"'"''
    ATTENDU="$(${COMPOSE} exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -Atc "${compter}")"
    OBTENU="$(${COMPOSE} exec -T db psql -U "${DB_USER}" -d "${VERIFY_DB}" -Atc "${compter}")"
    ${COMPOSE} exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" -qc "DROP DATABASE ${VERIFY_DB}" >/dev/null
    [[ "${OBTENU}" == "${ATTENDU}" ]] || die "restauration incomplete : ${OBTENU} tables sur ${ATTENDU}"
    log "Restauration verifiee : ${OBTENU} tables sur ${ATTENDU}"
fi

# ── Rotation (par anciennete, uniquement les sauvegardes validees) ─
find "${BACKUP_DIR}/daily" -maxdepth 1 -name 'budget_*.sql.gz' -type f \
    -mtime +"$((RETENTION_DAYS - 1))" -print -delete | sed 's/^/  supprime : /'
find "${BACKUP_DIR}/monthly" -maxdepth 1 -name 'budget_*.sql.gz' -type f \
    -mtime +"$((RETENTION_MONTHS * 31))" -print -delete | sed 's/^/  supprime : /'
# Restes de dumps interrompus (crash pendant une execution precedente)
find "${BACKUP_DIR}" -maxdepth 1 -name '.budget_*.partial' -type f -mmin +60 -delete

# ── Copie hors serveur (optionnelle) ──────────────────────────────
if [[ -n "${BACKUP_REMOTE}" ]]; then
    log "Copie vers ${BACKUP_REMOTE}..."
    rsync -a --delete "${BACKUP_DIR}/daily" "${BACKUP_DIR}/monthly" "${BACKUP_REMOTE}/" \
        || die "copie hors serveur echouee (la sauvegarde locale est conservee)"
fi

log "Termine : $(find "${BACKUP_DIR}/daily" -name 'budget_*.sql.gz' | wc -l) quotidienne(s), $(find "${BACKUP_DIR}/monthly" -name 'budget_*.sql.gz' | wc -l) mensuelle(s)."
