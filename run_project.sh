#!/usr/bin/env bash
# ==============================================================================
# TrustBridge AI - Script de configuration et lancement rapide pour le Hackathon
# ==============================================================================
set -e

echo "🚀 [TrustBridge AI] Initialisation de l'environnement Django..."

# 1. Vérification de l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "📦 Création du virtualenv Python..."
    python3 -m venv venv
fi

echo "🔌 Activation de l'environnement virtuel..."
source venv/bin/activate

# 2. Installation des dépendances
echo "📥 Installation des packages requirements.txt..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 3. Création du .env si absent
if [ ! -f ".env" ]; then
    echo "⚙️ Génération du fichier .env depuis .env.example..."
    cp .env.example .env
fi

# 4. Migrations SQLite
echo "🗄️ Application des migrations Django (SQLite)..."
python manage.py makemigrations core
python manage.py migrate

# 5. Création des données de test
echo "🌱 Chargement des données de démonstration..."
python manage.py seed_demo

# 6. Démarrage du serveur
echo "✅ Démarrage du serveur Django sur http://127.0.0.1:8000 ..."
python manage.py runserver 0.0.0.0:8000
