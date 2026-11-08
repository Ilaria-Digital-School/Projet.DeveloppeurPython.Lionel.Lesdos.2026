#!/bin/bash

# Fonction pour afficher l'utilisation du script
show_usage() {
    echo "Utilisation: $0 [options]"
    echo "Options:"
    echo "  -f, --force    Forcer l'arrêt sans demande de confirmation"
    echo "  -h, --help     Afficher ce message d'aide"
}

# Variables
FORCE=false

# Traitement des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Option non reconnue: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Définition des chemins
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/../.."
PID_FILE="$PROJECT_DIR/backend/tmp/flask.pid"
LOG_FILE="$PROJECT_DIR/backend/logs/app.log"

# Fonction pour trouver tous les processus Python liés à l'application
find_app_processes() {
    # Liste des motifs à chercher (moins stricts pour une meilleure détection)
    local patterns=(
        "python.*backend"
        "flask"
        "gunicorn"
    )
    
    # Pour chaque motif, trouver les PIDs correspondants
    local pids=()
    for pattern in "${patterns[@]}"; do
        while IFS= read -r pid; do
            # Vérifier que le PID est valide et n'est pas le script actuel
            if [ -n "$pid" ] && [ "$pid" != "$$" ]; then
                # Vérifier que le processus est bien python/flask
                if ps -p "$pid" -o command= | grep -v "stop\.sh" | grep -qE "${pattern//\\/}"; then
                    pids+=("$pid")
                fi
            fi
        done < <(pgrep -f "$pattern" 2>/dev/null || true)
    done
    
    # Afficher les PIDs uniques
    printf '%s\n' "${pids[@]}" | sort -u | grep -v "^\s*$"
}

# Vérification des processus en cours d'exécution
RUNNING_PROCESSES=$(find_app_processes)

if [ -z "$RUNNING_PROCESSES" ]; then
    echo "ℹ️  Aucun processus de l'application n'est en cours d'exécution."
    rm -f "$PID_FILE" 2>/dev/null
    exit 0
fi

# Fonction pour afficher les processus Python en cours d'exécution (débogage)
show_python_processes() {
    echo "\n🔍 Liste des processus Python en cours d'exécution :"
    ps aux | grep -i "python\|flask" | grep -v "grep"
}

# Affichage des processus en cours d'exécution
if [ -n "$RUNNING_PROCESSES" ]; then
    echo "🔍 Processus de l'application en cours d'exécution :"
    # Afficher les processus avec plus de détails
    ps -o pid,ppid,user,%cpu,%mem,cmd -p "$RUNNING_PROCESSES" 2>/dev/null || echo "  (Impossible d'afficher les détails des processus)"
    
    # Afficher les processus Python pour le débogage
    show_python_processes
else
    echo "ℹ️  Aucun processus de l'application n'est en cours d'exécution."
    show_python_processes
    exit 0
fi

# Demande de confirmation si pas en mode forcé
if [ "$FORCE" = false ]; then
    echo -n "\n⚠️  Voulez-vous arrêter ces processus ? [o/N] "
    read -r CONFIRM
    if [[ ! $CONFIRM =~ ^[oOyY].*$ ]]; then
        echo "❌ Opération annulée par l'utilisateur."
        exit 0
    fi
fi

# Arrêt des processus
echo "\n🛑 Arrêt des processus en cours d'exécution..."

# Convertir la liste des PIDs en tableau
IFS=$'\n' read -r -d '' -a pids_array <<< "$RUNNING_PROCESSES"

# 1. D'abord, essayer un arrêt propre
for pid in "${pids_array[@]}"; do
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null; then
        echo "  - Envoi de SIGTERM au PID $pid..."
        kill "$pid" 2>/dev/null || true
    fi
done

# Attendre un peu
sleep 2

# Vérifier les processus toujours en cours
STILL_RUNNING=$(find_app_processes)

# 2. Si nécessaire, forcer l'arrêt
if [ -n "$STILL_RUNNING" ]; then
    echo -e "\n⚠️  Certains processus ne répondent pas, arrêt forcé..."
    IFS=$'\n' read -r -d '' -a running_array <<< "$STILL_RUNNING"
    for pid in "${running_array[@]}"; do
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null; then
            echo "  - Envoi de SIGKILL au PID $pid..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
    sleep 1
fi

# Vérification finale
STILL_RUNNING=$(find_app_processes)
if [ -n "$STILL_RUNNING" ]; then
    echo "❌ Impossible d'arrêter les processus suivants :"
    ps -p $STILL_RUNNING -o pid,ppid,user,%cpu,%mem,cmd --no-headers
    exit 1
else
    # Nettoyage du fichier PID
    rm -f "$PID_FILE" 2>/dev/null
    
    # Affichage des dernières lignes du log si le fichier existe
    if [ -f "$LOG_FILE" ]; then
        echo "\n📝 Dernières lignes du journal d'application :"
        tail -n 5 "$LOG_FILE" | sed 's/^/  /'
    fi
    
    echo "\n✅ Tous les processus ont été arrêtés avec succès."
    exit 0
fi

# Affichage des informations de fin
echo ""
echo "🔍 Informations complémentaires :"
echo "- Fichier de log: $LOG_FILE"
echo "- Répertoire de l'application: $PROJECT_DIR"
echo ""
echo "🔄 Pour redémarrer l'application :"
echo "  ./backend/scripts/start.sh"
echo ""
echo "========================================"
echo ""
