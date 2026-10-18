# 🌉 TrustBridge AI - Escrow Intelligent & Django Architecture

> **Plateforme de séquestre (escrow) intelligente pour freelances avec vérification des livrables par l'IA Google Gemini et déblocage automatisé PayPal.**

---

## 🚀 Démarrage Rapide en Ligne de Commande (CLI)

Exécutez les étapes ci-dessous dans votre terminal pour initialiser et lancer le projet Django :

### 1. Cloner ou se placer dans le répertoire du projet
```bash
cd trustbridge_ai  # ou dans la racine du projet
```

### 2. Créer et activer l'environnement virtuel Python
```bash
# Création du venv Python 3.10+
python3 -m venv venv

# Activation sous Linux / macOS :
source venv/bin/activate

# Activation sous Windows (PowerShell) :
# .\venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement
Créez votre fichier `.env` à partir du fichier d'exemple :
```bash
cp .env.example .env
```
Renseignez vos clés dans le fichier `.env` :
- `GEMINI_API_KEY` : Clé d'API Google AI Studio (modèle `gemini-2.5-flash`).
- `PAYPAL_CLIENT_ID` et `PAYPAL_CLIENT_SECRET` : Identifiants Sandbox PayPal.

### 5. Appliquer les migrations de base de données (SQLite)
```bash
# Générer la migration initiale pour core.User
python manage.py makemigrations core

# Appliquer toutes les migrations vers db.sqlite3
python manage.py migrate
```

### 6. Charger les données de démonstration (Seed Hackathon)
Nous avons créé une commande personnalisée qui installe un compte Client, un compte Freelance avec email PayPal configuré, et un premier contrat de démonstration avec audit IA :
```bash
python manage.py seed_demo
```
> **Identifiants créés :**
> - **Superadmin** : `admin` / mot de passe : `admin1234`
> - **Client Démo** : `client_demo` / mot de passe : `hackathon2026`
> - **Freelance Démo** : `freelance_demo` / mot de passe : `hackathon2026` (PayPal : `freelance.escrow.receiver@sandbox.paypal.com`)

### 7. Démarrer le serveur de développement Django
```bash
python manage.py runserver 0.0.0.0:8000
```
Le projet est alors accessible sur :
- 🌐 Application Web : **http://localhost:8000/**
- 📊 Dashboard : **http://localhost:8000/dashboard/**
- 🛠️ Django Admin : **http://localhost:8000/admin/**

---

## 🏗️ Structure Architecturale du Projet

```
.
├── .env.example              # Template des secrets (PayPal Sandbox, Gemini API)
├── requirements.txt          # Dépendances (Django, google-genai, requests, python-dotenv)
├── manage.py                 # CLI d'administration Django
│
├── trustbridge/              # Package de configuration principal
│   ├── __init__.py
│   ├── settings.py           # Configuration SQLite, Auth User Model, PayPal, Gemini
│   ├── urls.py               # Routage global
│   ├── wsgi.py               # Entrée WSGI production
│   └── asgi.py               # Entrée ASGI production
│
├── core/                     # Application centrale TrustBridge
│   ├── __init__.py
│   ├── apps.py               # CoreConfig
│   ├── models.py             # User (AbstractUser, rôles CLIENT/FREELANCE), Contract, Deliverable, AIReviewReport
│   ├── admin.py              # Interface d'administration personnalisée avec filtres de rôles
│   ├── views.py              # Logique métier (séquestre, soumission, audit IA, déblocage)
│   ├── urls.py               # Routes d'application
│   │
│   ├── services/             # Couche d'intégration modulaire
│   │   ├── __init__.py
│   │   ├── paypal.py         # Service REST PayPal (OAuth2, Orders v2, Payouts API)
│   │   └── ai_review.py      # Service d'évaluation Gemini (SDK officiel google-genai)
│   │
│   └── management/commands/  # Commandes CLI personnalisées
│       └── seed_demo.py      # Script de peuplement rapide pour le hackathon
│
└── templates/                # Vues HTML avec Tailwind CSS
    ├── base.html             # Layout principal avec navbar réactive aux rôles
    └── core/
        ├── home.html         # Page d'accueil avec présentation du séquestre
        ├── dashboard.html    # Dashboard filtré par rôle
        ├── contract_detail.html # Détails du contrat, dépôt PayPal & rapport d'audit IA
        ├── create_contract.html # Création d'une mission avec critères d'acceptation
        ├── submit_deliverable.html # Soumission de code par le freelance
        └── login.html        # Formulaire d'authentification
```

---

## 🔒 Workflow de Séquestre & Audit IA

1. **Création du Contrat** : Le `CLIENT` définit le montant, le freelance assigné, le cahier des charges et la liste exacte des critères d'acceptation.
2. **Dépôt des Fonds** : Le client consigne le montant via l'API PayPal Orders v2 (`/v2/checkout/orders` et capture).
3. **Réalisation & Soumission** : Le `FREELANCE` développe la solution et soumet le code source ou l'URL du dépôt.
4. **Audit IA Instantané** : Le service `AIDeliverableReviewService` transmet le contrat, les critères et le livrable au modèle Google Gemini `gemini-2.5-flash` via le SDK `google-genai`. L'IA analyse la conformité et produit un score sur 100 avec un verdict strict (`PASS`, `REVISE` ou `FAIL`).
5. **Déblocage Automatisé** : Dès validation, les fonds sont instantanément transférés vers l'adresse `paypal_email` du freelance via l'API PayPal Payouts (`/v1/payments/payouts`).
