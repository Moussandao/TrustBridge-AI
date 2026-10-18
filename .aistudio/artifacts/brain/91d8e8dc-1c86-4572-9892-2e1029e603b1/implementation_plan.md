# TrustBridge AI - Architecture Fondatrice Django & Escrow Intelligent

TrustBridge AI est une plateforme de tiers de confiance (escrow) conçue pour sécuriser les transactions entre freelances et clients grâce au séquestre de fonds via PayPal et à l'arbitrage automatisé de conformité des livrables par l'IA Google Gemini. Ce plan détaille la mise en place de la fondation Django `trustbridge` avec son application centrale `core`, son modèle d'utilisateur personnalisé à double rôle, ses configurations de sécurité et ses outils d'exécution rapide.

### User Review & Critical Decisions

> [!IMPORTANT]
> Les choix suivants ont été confirmés pour adapter le socle technique aux exigences du hackathon et aux standards FinTech :
> - **Séquestre PayPal** : Utilisation de l'API REST PayPal v2 (Orders API pour la capture/autorisation des fonds et Payouts API pour le déblocage au freelance) avec support complet du mode Sandbox.
> - **Vérification IA** : Intégration du modèle `gemini-2.5-flash` via le SDK officiel `google-genai` pour une analyse multimodale performante (fichiers, codes, spécifications de contrat) à coût et latence maîtrisés.
> - **Organisation de projet** : Création d'une arborescence Django autonome et modulaire dans `trustbridge/` avec son app `core`, prête à être exécutée localement via CLI.

---

### 1. Overview & Core Concept

- **Problème résolu** : Dans le freelancing, les clients craignent de payer d'avance pour un travail incomplet ou non conforme, tandis que les freelances craignent de livrer sans garantie de paiement.
- **Solution TrustBridge AI** :
  1. Le client valide une mission et dépose les fonds en séquestre (Escrow) via PayPal Orders v2.
  2. Le freelance soumet son livrable (code source, documents, archives, maquettes).
  3. L'IA Gemini 2.5 Flash analyse la conformité du livrable par rapport aux critères d'acceptation du contrat et délivre un score et un rapport d'audit objectif.
  4. Dès validation, les fonds sont instantanément transférés sur le compte PayPal du freelance via l'API Payouts.
- **Rôles utilisateurs** :
  - `CLIENT` : Dépose les missions, finance le séquestre, consulte les rapports de conformité IA et valide les réceptions.
  - `FREELANCE` : Postule ou accepte les contrats, soumet les livrables avec notes explicatives, renseigne son email PayPal pour les versements automatiques.

---

### 2. User Experience & Visual Design

- **Identité visuelle FinTech & IA** :
  - Design professionnel et épuré avec Tailwind CSS (police sans-serif moderne, tons bleu marine ardoise `slate-900`, accents bleu royal `indigo-600` et vert validation `emerald-500`).
  - Badges distinctifs pour les statuts de séquestre : `FONDS SÉQUESTRÉS` (bleu), `EN AUDIT IA` (ambre pulsant), `CONFORME & LIBÉRÉ` (émeraude), `LITIGE` (rose/rouge).
- **Parcours utilisateur principal** :
  ```
  [Création Mission] ──> [Séquestre PayPal Client] ──> [Travail & Soumission Livrable]
                                                                  │
  [Déblocage Payouts PayPal] <── [Verdict Conforme] <── [Audit Gemini 2.5 Flash]
  ```
- **Templates & Rendu** :
  - Support de templates Django intégrés avec Tailwind CSS (CDN ou compilation) et structure modulaire `templates/base.html`, `templates/core/`.

---

### 3. Key Product Decisions & Trade-Offs

- **Base de données SQLite** :
  - *Choix* : `sqlite3` natif avec configuration de chemins fiables (`BASE_DIR / 'db.sqlite3'`).
  - *Pourquoi* : Zéro dépendance externe pour l'environnement hackathon, initialisation instantanée et portabilité parfaite.
- **Modèle Utilisateur personnalisé hérité d'`AbstractUser`** :
  - *Choix* : `User(AbstractUser)` défini dès la première migration avec `AUTH_USER_MODEL = 'core.User'`.
  - *Pourquoi* : Meilleure pratique absolue Django pour éviter les migrations destructives ultérieures lorsqu'on ajoute des champs métiers (`role`, `paypal_email`).
- **Gestion des secrets via `python-dotenv`** :
  - *Choix* : Chargement automatique d'un fichier `.env` avec valeurs de repli claires et template `.env.example`.
  - *Pourquoi* : Sécurité FinTech stricte évitant tout commit de jetons sensibles PayPal ou Gemini.
- **Architecture de Services Découplée** :
  - *Choix* : Création des dossiers `core/services/` avec `paypal.py` et `ai_review.py`.
  - *Pourquoi* : Évite l'engorgement des vues (`views.py`) et permet des tests unitaires isolés pour les API externes.

---

### 4. Technical Architecture & Data Strategy

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Projet Django "trustbridge"                     │
│                                                                        │
│  ┌──────────────────────┐               ┌───────────────────────────┐  │
│  │   trustbridge/       │               │          core/            │  │
│  │  - settings.py       │               │  - models.py (User, etc.) │  │
│  │  - urls.py           │               │  - views.py & urls.py     │  │
│  │  - wsgi.py / asgi.py │               │  - admin.py               │  │
│  └──────────┬───────────┘               └─────────────┬─────────────┘  │
│             │                                         │                │
│             └───────────────────┬─────────────────────┘                │
│                                 ▼                                      │
│                  ┌─────────────────────────────┐                       │
│                  │       core/services/        │                       │
│                  ├─────────────────────────────┤                       │
│                  │  paypal.py (Orders/Payouts) │                       │
│                  │  ai_review.py (Google GenAI)│                       │
│                  └──────────────┬──────────────┘                       │
└─────────────────────────────────┼──────────────────────────────────────┘
                                  │
             ┌────────────────────┴────────────────────┐
             ▼                                         ▼
   ┌───────────────────┐                     ┌───────────────────┐
   │ PayPal REST API   │                     │ Google GenAI SDK  │
   │ (Orders & Payouts)│                     │ (Gemini 2.5 Flash)│
   └───────────────────┘                     └───────────────────┘
```

#### Schéma des Données Fondateur (`models.py`)

- **Modèle `User`** :
  - `role`: `CharField` avec choix `CLIENT` ("Client / Donneur d'ordre") et `FREELANCE` ("Freelance / Prestataire").
  - `paypal_email`: `EmailField(blank=True, null=True)` pour la réception des fonds PayPal Payouts.
  - `created_at`: `DateTimeField(auto_now_add=True)`.

#### Structure des fichiers à générer :
- `requirements.txt` : Dépendances Python strictes et modernes (`Django>=5.1,<6.0`, `requests`, `google-genai`, `python-dotenv`, etc.).
- `manage.py` : Script de gestion Django standard.
- `trustbridge/settings.py` : Configuration de l'authentification `AUTH_USER_MODEL`, bases de données SQLite, templates, fichiers statiques, et variables d'environnement (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE`, `GEMINI_API_KEY`).
- `trustbridge/urls.py` : Routage principal.
- `trustbridge/wsgi.py` & `asgi.py` : Points d'entrée serveurs.
- `core/models.py` : Modèle utilisateur `User`.
- `core/admin.py` : Enregistrement de `User` dans l'interface d'administration Django avec personnalisation des champs.
- `core/apps.py` : Déclaration de l'application.
- `core/services/paypal.py` : Service d'interaction PayPal API (Authentification OAuth2, création d'ordres, capture, payouts).
- `core/services/ai_review.py` : Service d'analyse de conformité via `google-genai` et `gemini-2.5-flash`.
- `.env.example` : Template des variables d'environnement requises.
- Guide d'exécution CLI : Commandes étape par étape (création venv, installation, migrations, création superuser, lancement).
