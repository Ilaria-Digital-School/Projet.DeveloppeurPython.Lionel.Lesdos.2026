#!/usr/bin/env bash
# =============================================================================
# Script d'installation - Application de Gestion Budgetaire
# Usage: ./setup.sh [--docker | --local]
# =============================================================================
set -euo pipefail

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Répertoire racine du projet
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${PROJECT_DIR}/.env"
ENV_EXAMPLE="${PROJECT_DIR}/.env.example"

# =============================================================================
# Fonctions utilitaires
# =============================================================================

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERREUR]${NC} $1" >&2; }

check_command() {
    if ! command -v "$1" &>/dev/null; then
        error "$1 n'est pas installe."
        return 1
    fi
    success "$1 est disponible."
}

generate_secret() {
    python3 -c "import secrets; print(secrets.token_hex(32))"
}

prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local result
    read -rp "$(echo -e "${BLUE}${prompt}${NC} [${default}]: ")" result
    echo "${result:-$default}"
}

# =============================================================================
# Vérification des prérequis
# =============================================================================

check_prerequisites_common() {
    info "Verification des prerequis communs..."
    check_command python3
    check_command pip3 || check_command pip
}

check_prerequisites_docker() {
    info "Verification des prerequis Docker..."
    check_command docker
    check_command "docker compose" 2>/dev/null || docker compose version &>/dev/null || {
        error "docker compose n'est pas disponible. Installez Docker Compose V2."
        exit 1
    }
    success "docker compose est disponible."
}

check_prerequisites_local() {
    info "Verification des prerequis locaux..."
    check_command python3

    # Vérifier PostgreSQL client
    if ! command -v psql &>/dev/null; then
        warn "psql (client PostgreSQL) n'est pas installe."
        warn "Installez-le avec : sudo apt install postgresql-client"
    else
        success "psql est disponible."
    fi
}

# =============================================================================
# Génération du fichier .env
# =============================================================================

setup_env_file() {
    info "Configuration du fichier .env..."

    if [ -f "$ENV_FILE" ]; then
        warn "Le fichier .env existe deja."
        local overwrite
        read -rp "Voulez-vous le recreer ? (o/N): " overwrite
        if [[ ! "$overwrite" =~ ^[oOyY]$ ]]; then
            info "Conservation du .env existant."
            return 0
        fi
    fi

    # Copier le template
    cp "$ENV_EXAMPLE" "$ENV_FILE"

    # Générer les clés secrètes
    info "Generation des cles secretes..."
    local secret_key jwt_secret csrf_secret password_salt
    secret_key=$(generate_secret)
    jwt_secret=$(generate_secret)
    csrf_secret=$(generate_secret)
    password_salt=$(generate_secret)

    # Remplacer les valeurs dans .env
    sed -i "s|SECRET_KEY=.*|SECRET_KEY='${secret_key}'|" "$ENV_FILE"
    sed -i "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY='${jwt_secret}'|" "$ENV_FILE"
    sed -i "s|WTF_CSRF_SECRET_KEY=.*|WTF_CSRF_SECRET_KEY='${csrf_secret}'|" "$ENV_FILE"
    sed -i "s|CSRF_SECRET_KEY=.*|CSRF_SECRET_KEY='${csrf_secret}'|" "$ENV_FILE"

    # Ajouter SECURITY_PASSWORD_SALT s'il n'existe pas
    if ! grep -q "SECURITY_PASSWORD_SALT" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# Sel pour le hachage des mots de passe" >> "$ENV_FILE"
        echo "SECURITY_PASSWORD_SALT='${password_salt}'" >> "$ENV_FILE"
    else
        sed -i "s|SECURITY_PASSWORD_SALT=.*|SECURITY_PASSWORD_SALT='${password_salt}'|" "$ENV_FILE"
    fi

    # Demander les credentials PostgreSQL
    echo ""
    info "Configuration de la base de donnees PostgreSQL :"
    local db_user db_password db_name
    db_user=$(prompt_with_default "Utilisateur PostgreSQL" "budget_user")
    db_password=$(prompt_with_default "Mot de passe PostgreSQL" "$(generate_secret | cut -c1-16)")
    db_name=$(prompt_with_default "Nom de la base de donnees" "budget")

    # Mettre à jour les variables PostgreSQL
    sed -i "s|POSTGRES_DB=.*|POSTGRES_DB=${db_name}|" "$ENV_FILE"
    sed -i "s|POSTGRES_USER=.*|POSTGRES_USER=${db_user}|" "$ENV_FILE"
    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${db_password}|" "$ENV_FILE"

    # Variables exportées pour usage dans les fonctions suivantes
    export DB_USER="$db_user"
    export DB_PASSWORD="$db_password"
    export DB_NAME="$db_name"

    success "Fichier .env genere avec des cles securisees."
}

# =============================================================================
# Mode Docker
# =============================================================================

setup_docker() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Installation Docker${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    check_prerequisites_docker
    setup_env_file

    # Mettre à jour DATABASE_URL pour Docker (le service s'appelle "db")
    local db_user="${DB_USER:-budget_user}"
    local db_password="${DB_PASSWORD:-password}"
    local db_name="${DB_NAME:-budget}"
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql://${db_user}:${db_password}@db:5432/${db_name}|" "$ENV_FILE"

    success "DATABASE_URL configuree pour Docker (host=db)."

    # Lancer Docker Compose
    info "Construction et demarrage des conteneurs..."
    cd "$PROJECT_DIR"
    docker compose up --build -d

    # Attendre le healthcheck
    info "Attente du demarrage de PostgreSQL..."
    local retries=30
    while [ $retries -gt 0 ]; do
        if docker compose exec db pg_isready -U "$db_user" -d "$db_name" &>/dev/null; then
            success "PostgreSQL est pret."
            break
        fi
        retries=$((retries - 1))
        sleep 2
    done

    if [ $retries -eq 0 ]; then
        error "PostgreSQL n'a pas demarre dans le delai imparti."
        echo "Verifiez les logs : docker compose logs db"
        exit 1
    fi

    # Appliquer les migrations
    info "Application des migrations..."
    docker compose exec app flask db upgrade

    echo ""
    success "Installation terminee !"
    echo ""
    echo -e "${GREEN}L'application est accessible sur :${NC}"
    echo -e "  ${BLUE}http://localhost:8080${NC}"
    echo ""
    echo -e "Commandes utiles :"
    echo -e "  docker compose logs -f app     # Voir les logs"
    echo -e "  docker compose exec app flask create-admin  # Creer un admin"
    echo -e "  docker compose down            # Arreter les services"
}

# =============================================================================
# Mode Local
# =============================================================================

setup_local() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Installation locale${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    check_prerequisites_local
    setup_env_file

    # Mettre à jour DATABASE_URL pour local (localhost)
    local db_user="${DB_USER:-budget_user}"
    local db_password="${DB_PASSWORD:-password}"
    local db_name="${DB_NAME:-budget}"
    sed -i "s|DATABASE_URL=.*postgresql.*|DATABASE_URL=postgresql://${db_user}:${db_password}@localhost:5432/${db_name}|" "$ENV_FILE"
    sed -i "s|REDIS_URL=redis://redis:|REDIS_URL=redis://localhost:|" "$ENV_FILE"

    success "DATABASE_URL et REDIS_URL configurees pour usage local."

    # Vérifier la connectivité PostgreSQL
    info "Verification de la connexion a PostgreSQL..."
    if command -v psql &>/dev/null && psql "postgresql://${db_user}:${db_password}@localhost:5432/${db_name}" -c "SELECT 1;" &>/dev/null; then
        success "Connexion a PostgreSQL reussie."
    else
        warn "Impossible de se connecter a PostgreSQL."
        echo ""
        echo "  Assurez-vous que PostgreSQL est demarre et que la base '${db_name}' existe :"
        echo ""
        echo "    sudo -u postgres psql -c \"CREATE USER ${db_user} WITH PASSWORD '${db_password}';\""
        echo "    sudo -u postgres psql -c \"CREATE DATABASE ${db_name} OWNER ${db_user};\""
        echo "    sudo -u postgres psql -c \"CREATE DATABASE ${db_name}_test OWNER ${db_user};\""
        echo ""
        echo "  Ou lancez PostgreSQL via Docker :"
        echo "    docker run -d --name budget-postgres -p 5432:5432 \\"
        echo "      -e POSTGRES_USER=${db_user} -e POSTGRES_PASSWORD=${db_password} \\"
        echo "      -e POSTGRES_DB=${db_name} postgres:16-alpine"
        echo ""
    fi

    # Créer le virtualenv
    info "Creation de l'environnement virtuel Python..."
    cd "$PROJECT_DIR"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        success "Environnement virtuel cree."
    else
        info "Environnement virtuel existant detecte."
    fi

    # Activer et installer les dépendances
    # shellcheck disable=SC1091
    source venv/bin/activate
    info "Installation des dependances Python..."
    pip install --quiet --upgrade pip
    pip install --quiet -r backend/requirements.txt
    success "Dependances installees."

    # Appliquer les migrations
    info "Application des migrations de base de donnees..."
    cd "$PROJECT_DIR/backend"
    if flask db upgrade 2>/dev/null; then
        success "Migrations appliquees."
    else
        warn "Echec des migrations. Verifiez la connexion a PostgreSQL."
    fi

    # Proposer la création d'un admin
    echo ""
    local create_admin
    read -rp "Voulez-vous creer un compte administrateur ? (O/n): " create_admin
    if [[ ! "$create_admin" =~ ^[nN]$ ]]; then
        flask create-admin
    fi

    echo ""
    success "Installation terminee !"
    echo ""
    echo -e "${GREEN}Pour demarrer l'application :${NC}"
    echo ""
    echo "  cd ${PROJECT_DIR}"
    echo "  source venv/bin/activate"
    echo "  cd backend"
    echo "  flask run --debug --port 8080"
    echo ""
    echo -e "L'application sera accessible sur : ${BLUE}http://localhost:8080${NC}"
}

# =============================================================================
# Point d'entrée principal
# =============================================================================

show_usage() {
    echo "Usage: $0 [--docker | --local]"
    echo ""
    echo "Options :"
    echo "  --docker    Installation avec Docker (recommande)"
    echo "  --local     Installation locale (developpement)"
    echo ""
    echo "Sans argument, un menu interactif est affiche."
}

main() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Application de Gestion Budgetaire - Installation ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    case "${1:-}" in
        --docker)
            setup_docker
            ;;
        --local)
            setup_local
            ;;
        --help|-h)
            show_usage
            ;;
        "")
            echo "Choisissez le mode d'installation :"
            echo ""
            echo "  1) Docker (recommande) - PostgreSQL + Redis + App conteneurises"
            echo "  2) Local              - venv Python + PostgreSQL local"
            echo ""
            local choice
            read -rp "Votre choix (1/2): " choice
            case "$choice" in
                1) setup_docker ;;
                2) setup_local ;;
                *) error "Choix invalide."; exit 1 ;;
            esac
            ;;
        *)
            error "Option inconnue : $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
