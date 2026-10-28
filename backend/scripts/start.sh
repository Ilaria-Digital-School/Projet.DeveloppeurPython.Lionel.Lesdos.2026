#!/bin/bash

# Fonction pour trouver un port disponible
find_available_port() {
    local port=$1
    while lsof -i :$port > /dev/null 2>&1; do
        echo "Port $port est déjà utilisé, essai du port suivant..."
        port=$((port + 1))
    done
    echo $port
}

# Fonction pour afficher un message d'en-tête
print_header() {
    echo "\n========================================"
    echo "  Gestionnaire d'Application Budgétaire"
    echo "========================================"
}

# Afficher l'en-tête
print_header

# Afficher le répertoire courant
echo "📂 Répertoire: $(pwd)"

# Chemin vers l'environnement virtuel
VENV_PATH="$(dirname "$0")/../../venv"
echo "🔧 Environnement virtuel: $VENV_PATH"

# Vérifier si le répertoire venv existe
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Erreur: L'environnement virtuel n'existe pas: $VENV_PATH"
    echo "   Créez-le avec: python -m venv venv"
    exit 1
fi

# Activer l'environnement virtuel
echo "🚀 Activation de l'environnement virtuel..."
source "$VENV_PATH/bin/activate"

# Vérifier si l'activation a réussi
if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de l'activation de l'environnement virtuel"
    exit 1
fi

# Mettre à jour pip
echo "🔄 Mise à jour de pip..."
python -m pip install --upgrade pip

# Se déplacer dans le répertoire racine du projet
PROJECT_ROOT="$(dirname "$0")/../.."
cd "$PROJECT_ROOT"

# Vérifier et installer les dépendances
if [ -f "backend/requirements.txt" ]; then
    echo "📦 Vérification des dépendances..."
    
    # Vérifier si pip est à jour
    pip install --upgrade pip
    
    # Installer les dépendances
    echo "🔍 Installation des dépendances..."
    pip install -r backend/requirements.txt
    
    # Vérifier les mises à jour disponibles
    echo "🔎 Vérification des mises à jour disponibles..."
    outdated=$(pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1)
    
    if [ -n "$outdated" ]; then
        echo "📢 Mises à jour disponibles pour les packages suivants :"
        echo "$outdated" | sed 's/^/   - /'
        echo "\nPour mettre à jour, exécutez : pip install --upgrade $(echo "$outdated" | tr '\n' ' ')"
    else
        echo "✅ Toutes les dépendances sont à jour."
    fi
else
    echo "❌ Fichier requirements.txt introuvable dans le répertoire backend/"
    exit 1
fi

# Exporter les variables d'environnement nécessaires
export FLASK_APP=backend/app.py
export FLASK_ENV=development
export PYTHONPATH="$PWD:$PYTHONPATH"

echo "\n⚙️  Configuration :"
echo "   - FLASK_APP=$FLASK_APP"
echo "   - FLASK_ENV=$FLASK_ENV"
echo "   - PYTHONPATH=$PYTHONPATH"

# Trouver un port disponible
PORT=5001
AVAILABLE_PORT=$(find_available_port $PORT)

echo "\n🚀 Démarrage de l'application sur http://localhost:$AVAILABLE_PORT"
echo "   Appuyez sur Ctrl+C pour arrêter le serveur\n"

# Lancer l'application Flask
cd backend
python -m flask run --host=0.0.0.0 --port=$AVAILABLE_PORT

# Gestion de l'arrêt
echo "\n🛑 Arrêt du serveur..."

# Conserver le terminal ouvert en cas d'erreur
if [ $? -ne 0 ]; then
    echo "\n❌ L'application s'est arrêtée avec une erreur."
    echo "   Vérifiez les logs ci-dessus pour plus d'informations."
    echo "\nAppuyez sur Entrée pour quitter..."
    read
fi
