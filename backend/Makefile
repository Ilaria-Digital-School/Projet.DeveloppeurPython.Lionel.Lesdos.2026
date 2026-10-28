.PHONY: install test lint format clean run init-db upgrade-db downgrade-db shell

# Variables
VENV = ../venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
FLASK = $(VENV)/bin/flask
PYTEST = $(VENV)/bin/pytest
BLACK = $(VENV)/bin/black
FLAKE8 = $(VENV)/bin/flake8
ISORT = $(VENV)/bin/isort

# Installation des dépendances
install:
	$(PIP) install -r ../requirements.txt

# Exécution des tests
test:
	$(PYTEST) -v --cov=. tests/

# Vérification du style de code
lint:
	$(FLAKE8 .
	$(BLACK) --check .
	$(ISORT) --check-only .

# Formatage du code
format:
	$(BLACK) .
	$(ISORT) .

# Nettoyage des fichiers temporaires
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +

# Démarrer l'application en mode développement
run:
	$(FLASK) run --port=5000

# Initialiser la base de données
init-db:
	$(FLASK) db init
	$(FLASK) db migrate -m "Initial migration"
	$(FLASK) db upgrade
	$(PYTHON) ../init_db.py

# Mettre à jour la base de données
upgrade-db:
	$(FLASK) db upgrade

# Revenir à la version précédente de la base de données
downgrade-db:
	$(FLASK) db downgrade -1

# Lancer un shell Python avec le contexte de l'application
shell:
	$(FLASK) shell

# Aide
dev: install init-db run

help:
	@echo "Commandes disponibles :"
	@echo "  make install      Installer les dépendances"
	@echo "  make test        Exécuter les tests"
	@echo "  make lint        Vérifier le style de code"
	@echo "  make format      Formater le code"
	@echo "  make clean       Nettoyer les fichiers temporaires"
	@echo "  make run         Démarrer l'application en mode développement"
	@echo "  make init-db     Initialiser la base de données"
	@echo "  make upgrade-db  Mettre à jour la base de données"
	@echo "  make downgrade-db Revenir à la version précédente de la base de données"
	@echo "  make shell       Lancer un shell Python avec le contexte de l'application"
	@echo "  make dev         Installer, initialiser et démarrer l'application"
