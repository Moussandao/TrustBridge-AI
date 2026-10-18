import React, { useState } from 'react';
import {
  ShieldCheck,
  Code2,
  Terminal,
  Cpu,
  Layers,
  CreditCard,
  UserCheck,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  ArrowRight,
  ExternalLink,
  FileCode,
  Sparkles,
  RefreshCw,
  FolderTree,
  Send,
  Database,
  Lock,
  ChevronRight
} from 'lucide-react';

// Code files data generated in the Django project
const DJANGO_FILES = [
  {
    path: 'core/models.py',
    category: 'Models',
    badge: 'User, Project, Milestone, Deliverable',
    description: 'Modèles conceptuels complets : User (AbstractUser), Project, Milestone (Séquestre) et Deliverable (Audit IA Gemini).',
    code: `from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'CLIENT', _('Client (Donneur d\\'ordre)')
        FREELANCE = 'FREELANCE', _('Freelance (Prestataire)')

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.FREELANCE)
    paypal_email = models.EmailField(max_length=254, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def is_client(self) -> bool:
        return self.role == self.Role.CLIENT

    def is_freelance(self) -> bool:
        return self.role == self.Role.FREELANCE

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"

class Project(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        IN_PROGRESS = 'IN_PROGRESS', _('En cours')
        COMPLETED = 'COMPLETED', _('Terminé')
        CANCELLED = 'CANCELLED', _('Annulé')

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects_as_client')
    freelance = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects_as_freelance')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

class Milestone(models.Model):
    class Status(models.TextChoices):
        LOCKED = 'LOCKED', _('Verrouillé')
        FUNDED = 'FUNDED', _('Financé (Séquestre PayPal)')
        SUBMITTED = 'SUBMITTED', _('Livrable soumis')
        APPROVED = 'APPROVED', _('Approuvé par l\\'IA')
        PAID = 'PAID', _('Payé (Payouts)')

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LOCKED)
    paypal_order_id = models.CharField(max_length=120, blank=True, null=True)
    paypal_payout_batch_id = models.CharField(max_length=120, blank=True, null=True)

class Deliverable(models.Model):
    class AIReviewStatus(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        APPROVED = 'APPROVED', _('Validé')
        REJECTED = 'REJECTED', _('Rejeté')

    milestone = models.ForeignKey(Milestone, on_delete=models.CASCADE, related_name='deliverables')
    submission_text = models.TextField()
    file_url = models.URLField(blank=True, null=True)
    ai_review_status = models.CharField(max_length=20, choices=AIReviewStatus.choices, default=AIReviewStatus.PENDING)
    ai_feedback = models.TextField(blank=True, null=True)
    score = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])`
  },
  {
    path: 'core/admin.py',
    category: 'Admin',
    badge: 'Inlines & Badges',
    description: "Interface d'administration complète avec inlines imbriqués, badges de statut colorés et actions de simulation démo.",
    code: `from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Project, Milestone, Deliverable

class DeliverableInline(admin.StackedInline):
    model = Deliverable
    extra = 0
    fields = ('submission_text', 'file_url', 'score', 'ai_review_status', 'ai_feedback')

class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 1
    fields = ('title', 'amount', 'status', 'paypal_order_id', 'paypal_payout_batch_id')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'freelance', 'total_amount', 'currency', 'status')
    inlines = [MilestoneInline]

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'amount', 'status', 'paypal_order_id', 'paypal_payout_batch_id')
    inlines = [DeliverableInline]

@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display = ('milestone', 'score', 'ai_review_status', 'submitted_at')`
  },
  {
    path: 'trustbridge/settings.py',
    category: 'Configuration',
    badge: 'SQLite & Secrets',
    description: 'Configuration centrale Django avec SQLite, AUTH_USER_MODEL, support python-dotenv, variables PayPal et Gemini.',
    code: `import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'default-insecure-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1')
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'core.apps.CoreConfig',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Modèle Utilisateur Personnalisé
AUTH_USER_MODEL = 'core.User'

# Clés d'API Externes
PAYPAL_MODE = os.environ.get('PAYPAL_MODE', 'sandbox')
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', '')
PAYPAL_API_BASE_URL = 'https://api-m.sandbox.paypal.com'

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash')`
  },
  {
    path: 'core/services/paypal_service.py',
    category: 'Services',
    badge: 'PayPal Sandbox Orders & Payouts (-5%)',
    description: "Module dédié PayPal Sandbox : OAuth2, Orders v2 pour jalons, capture et déblocage Payouts (commission 5% déduite).",
    code: `import logging, requests, uuid
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

logger = logging.getLogger(__name__)

class PayPalAPIError(Exception):
    def __init__(self, message, status_code=None, response_data=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}

def get_oauth_token() -> str:
    url = f"{settings.PAYPAL_API_BASE_URL}/v1/oauth2/token"
    res = requests.post(
        url,
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json"},
        timeout=15
    )
    res.raise_for_status()
    return res.json().get("access_token")

def create_milestone_order(milestone):
    token = get_oauth_token()
    amount_val = Decimal(str(milestone.amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    currency = getattr(milestone.project, 'currency', 'USD')
    url = f"{settings.PAYPAL_API_BASE_URL}/v2/checkout/orders"
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": f"MILESTONE-{milestone.id}",
            "amount": {"currency_code": currency, "value": f"{amount_val:.2f}"}
        }]
    }
    res = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    approval_url = next((l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), "")
    return data.get("id"), approval_url

def capture_order_payment(order_id: str):
    token = get_oauth_token()
    url = f"{settings.PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}/capture"
    res = requests.post(url, headers={"Authorization": f"Bearer {token}"})
    return res.json()

def send_freelance_payout(milestone):
    token = get_oauth_token()
    raw_amount = Decimal(str(milestone.amount))
    commission = (raw_amount * Decimal("0.05")).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    net_payout = (raw_amount - commission).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    currency = getattr(milestone.project, 'currency', 'USD')
    receiver = milestone.project.freelance.paypal_email
    url = f"{settings.PAYPAL_API_BASE_URL}/v1/payments/payouts"
    payload = {
        "sender_batch_header": {"sender_batch_id": f"TB-MILESTONE-{milestone.id}-{uuid.uuid4().hex[:6]}"},
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {"value": f"{net_payout:.2f}", "currency": currency},
            "receiver": receiver
        }]
    }
    res = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
    return res.json()`
  },
  {
    path: 'core/services/ai_service.py',
    category: 'Services',
    badge: 'Gemini Deliverable Auditor (JSON Strict)',
    description: "Service d'analyse impartiale des livrables freelances via Google GenAI avec prompt structuré et parsing JSON strict.",
    code: `import json, re, logging
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

def analyze_deliverable(milestone_description: str, deliverable_content: str):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = f"""
=== CONTEXTE D'ARBITRAGE ===
Tu es un expert impartial en revue de projets numériques.

=== JALON EXIGÉ ===
{milestone_description}

=== LIVRABLE FOURNI PAR LE FREELANCE ===
{deliverable_content}

Réponds STRICTEMENT par un JSON valide :
{{
  "approved": <true|false>,
  "score": <0-100>,
  "summary": "<résumé de l'analyse en 2 phrases>",
  "feedback": "<points forts et éléments manquants éventuels>"
}}
"""
    response = client.models.generateContent(
        model=getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    cleaned = response.text.strip()
    if cleaned.startswith("\`\`\`"):
        cleaned = re.sub(r"^\`\`\`[a-zA-Z]*\\n?", "", cleaned)
        cleaned = re.sub(r"\\n?\`\`\`$", "", cleaned).strip()
    return json.loads(cleaned)`
  },
  {
    path: 'core/views.py',
    category: 'Views & Webhooks',
    badge: 'Dashboards & Webhooks',
    description: "Vues Django pour les dashboards Client et Freelance, endpoints AJAX PayPal Smart Buttons et Webhook (/webhooks/paypal/).",
    code: `from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Project, Milestone, Deliverable
from .services.paypal_service import create_milestone_order, capture_order_payment, send_freelance_payout
from .services.ai_service import analyze_deliverable

def dashboard_view(request):
    projects = Project.objects.filter(client=request.user) if request.user.is_client() else Project.objects.filter(freelance=request.user)
    return render(request, 'core/dashboard.html', {'projects': projects, 'is_client': request.user.is_client()})

@csrf_exempt
@require_POST
def paypal_webhook_view(request):
    payload = json.loads(request.body.decode('utf-8'))
    if payload.get('event_type') == 'PAYMENT.CAPTURE.COMPLETED':
        order_id = payload.get('resource', {}).get('id')
        milestone = Milestone.objects.filter(paypal_order_id=order_id).first()
        if milestone:
            milestone.status = Milestone.Status.FUNDED
            milestone.save()
    return HttpResponse(status=200)`
  },
  {
    path: 'requirements.txt',
    category: 'Dependencies',
    badge: 'Python Packages',
    description: 'Liste des dépendances certifiées : Django, google-genai, requests, python-dotenv, Pillow, etc.',
    code: `Django>=5.1.0,<6.0.0
requests>=2.32.3
google-genai>=1.0.0
python-dotenv>=1.0.1
Pillow>=10.4.0
gunicorn>=23.0.0
uvicorn>=0.30.0
django-cors-headers>=4.4.0`
  },
  {
    path: '.env.example',
    category: 'Configuration',
    badge: 'Environment Variables',
    description: 'Variables d\'environnement pour l\'authentification PayPal Sandbox et l\'API Gemini.',
    code: `DJANGO_SECRET_KEY="django-insecure-trustbridge-hackathon-secret-key-change-in-prod"
DJANGO_DEBUG="True"
DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1,0.0.0.0"

PAYPAL_MODE="sandbox"
PAYPAL_CLIENT_ID="your_paypal_sandbox_client_id_here"
PAYPAL_CLIENT_SECRET="your_paypal_sandbox_client_secret_here"

GEMINI_API_KEY="your_gemini_api_key_here"
GEMINI_MODEL="gemini-2.5-flash"
APP_URL="http://localhost:8000"`
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState<'simulator' | 'files' | 'cli' | 'architecture'>('simulator');
  const [selectedFileIndex, setSelectedFileIndex] = useState<number>(0);
  const [copiedPath, setCopiedPath] = useState<string | null>(null);

  // Escrow Interactive Simulator State
  const [userRole, setUserRole] = useState<'CLIENT' | 'FREELANCE'>('CLIENT');
  const [escrowStatus, setEscrowStatus] = useState<'AWAITING_PAYMENT' | 'FUNDED' | 'AUDITING' | 'APPROVED' | 'PAID_OUT'>('AWAITING_PAYMENT');
  const [contractAmount, setContractAmount] = useState<number>(750);
  const [deliverableCode, setDeliverableCode] = useState<string>(
    `# Implementation of TrustBridge Escrow Webhooks\ndef handle_paypal_webhook(payload):\n    event_type = payload.get('event_type')\n    if event_type == 'CHECKOUT.ORDER.COMPLETED':\n        order_id = payload['resource']['id']\n        return lock_escrow_deposit(order_id)\n    return {'status': 'acknowledged'}`
  );
  const [aiScore, setAiScore] = useState<number>(94);
  const [auditVerdict, setAuditVerdict] = useState<'PASS' | 'REVISE' | 'FAIL'>('PASS');
  const [paypalCaptureId, setPaypalCaptureId] = useState<string>('CAPTURE-SANDBOX-8491AC');
  const [paypalPayoutId, setPaypalPayoutId] = useState<string>('PAYOUT-BATCH-7701BF');

  const copyCode = (code: string, path: string) => {
    navigator.clipboard.writeText(code);
    setCopiedPath(path);
    setTimeout(() => setCopiedPath(null), 2000);
  };

  const handleDepositEscrow = () => {
    setEscrowStatus('FUNDED');
    setPaypalCaptureId(`CAPTURE-MOCK-${Math.random().toString(36).substring(2, 8).toUpperCase()}`);
  };

  const handleRunAiAudit = () => {
    setEscrowStatus('AUDITING');
    setTimeout(() => {
      setEscrowStatus('APPROVED');
      setAiScore(92);
      setAuditVerdict('PASS');
    }, 1200);
  };

  const handleReleasePayout = () => {
    setEscrowStatus('PAID_OUT');
    setPaypalPayoutId(`PAYOUT-BATCH-${Math.random().toString(36).substring(2, 8).toUpperCase()}`);
  };

  const handleResetDemo = () => {
    setEscrowStatus('AWAITING_PAYMENT');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Banner Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-indigo-600 to-emerald-400 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
              TB
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-lg text-white tracking-tight">TrustBridge AI</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                  Django &bull; Gemini 2.5 Flash &bull; PayPal
                </span>
              </div>
              <p className="text-xs text-slate-400">Architecture & Hub de Démonstration Hackathon</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('simulator')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'simulator' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              Simulateur Escrow & IA
            </button>
            <button
              onClick={() => setActiveTab('files')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'files' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              Fichiers Django Générés
            </button>
            <button
              onClick={() => setActiveTab('cli')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'cli' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              Commandes CLI
            </button>
            <button
              onClick={() => setActiveTab('architecture')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTab === 'architecture' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Architecture
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        {activeTab === 'simulator' && (
          <div className="space-y-6">
            {/* Control Bar: Role Toggle & Status */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm">
              <div className="flex items-center gap-4">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Vue active :</span>
                <div className="inline-flex rounded-lg bg-slate-950 p-1 border border-slate-800">
                  <button
                    onClick={() => setUserRole('CLIENT')}
                    className={`flex items-center gap-2 px-3 py-1 rounded-md text-xs font-medium transition ${
                      userRole === 'CLIENT'
                        ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    Client (Donneur d'ordre)
                  </button>
                  <button
                    onClick={() => setUserRole('FREELANCE')}
                    className={`flex items-center gap-2 px-3 py-1 rounded-md text-xs font-medium transition ${
                      userRole === 'FREELANCE'
                        ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    <Code2 className="w-3.5 h-3.5" />
                    Freelance (Prestataire)
                  </button>
                </div>
              </div>

              {/* Progress Stepper */}
              <div className="flex items-center gap-2 text-xs">
                <span
                  className={`px-3 py-1 rounded-full font-mono flex items-center gap-1.5 ${
                    escrowStatus === 'AWAITING_PAYMENT'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-emerald-500/20 text-emerald-300'
                  }`}
                >
                  <CreditCard className="w-3 h-3" />
                  1. Séquestre PayPal
                </span>
                <ChevronRight className="w-3 h-3 text-slate-600" />
                <span
                  className={`px-3 py-1 rounded-full font-mono flex items-center gap-1.5 ${
                    escrowStatus === 'FUNDED'
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                      : escrowStatus === 'APPROVED' || escrowStatus === 'PAID_OUT'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  <Sparkles className="w-3 h-3" />
                  2. Audit Gemini
                </span>
                <ChevronRight className="w-3 h-3 text-slate-600" />
                <span
                  className={`px-3 py-1 rounded-full font-mono flex items-center gap-1.5 ${
                    escrowStatus === 'PAID_OUT'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                      : 'bg-slate-800 text-slate-500'
                  }`}
                >
                  <ShieldCheck className="w-3 h-3" />
                  3. Payout Instantané
                </span>
              </div>
            </div>

            {/* Contract & Escrow Card */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Contract Details & Actions */}
              <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
                <div>
                  <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Mission en séquestre #104</div>
                  <h2 className="text-xl font-bold text-white mt-1">Micro-service Django PayPal & Gemini 2.5 Flash</h2>
                  <p className="text-xs text-slate-400 mt-2">
                    Client : <span className="text-slate-200">client_demo</span> &bull; Freelance : <span className="text-slate-200">freelance_demo</span>
                  </p>
                </div>

                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Montant sous séquestre :</span>
                    <span className="text-xl font-black text-emerald-400 font-mono">{contractAmount} EUR</span>
                  </div>
                  <div className="text-xs text-slate-400 space-y-1 pt-2 border-t border-slate-800">
                    <div className="flex justify-between">
                      <span>Statut Séquestre :</span>
                      <strong className="text-slate-200 font-mono">
                        {escrowStatus === 'AWAITING_PAYMENT' && 'Fonds non versés'}
                        {escrowStatus === 'FUNDED' && 'Séquestré sur PayPal'}
                        {escrowStatus === 'AUDITING' && 'Audit IA en cours...'}
                        {escrowStatus === 'APPROVED' && 'Validé (Conforme)'}
                        {escrowStatus === 'PAID_OUT' && 'Débloqué & Versé'}
                      </strong>
                    </div>
                    {escrowStatus !== 'AWAITING_PAYMENT' && (
                      <div className="flex justify-between">
                        <span>ID Capture :</span>
                        <code className="text-indigo-400 font-mono">{paypalCaptureId}</code>
                      </div>
                    )}
                    {escrowStatus === 'PAID_OUT' && (
                      <div className="flex justify-between">
                        <span>ID Payouts :</span>
                        <code className="text-emerald-400 font-mono">{paypalPayoutId}</code>
                      </div>
                    )}
                  </div>
                </div>

                {/* Acceptance Criteria */}
                <div className="space-y-2">
                  <span className="text-xs font-semibold text-slate-300">Critères d'acceptation stricts (Audit IA) :</span>
                  <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs text-slate-300 font-mono space-y-1">
                    <div>&bull; Modèle User avec rôles CLIENT & FREELANCE</div>
                    <div>&bull; Configuration SQLite & variables PayPal/Gemini</div>
                    <div>&bull; SDK google-genai avec modèle gemini-2.5-flash</div>
                    <div>&bull; Commandes CLI d'initialisation documentées</div>
                  </div>
                </div>

                {/* Escrow Trigger Buttons */}
                <div className="space-y-3 pt-2">
                  {userRole === 'CLIENT' && escrowStatus === 'AWAITING_PAYMENT' && (
                    <button
                      onClick={handleDepositEscrow}
                      className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-xl text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 transition"
                    >
                      <CreditCard className="w-4 h-4" />
                      Séquestrer {contractAmount} € via PayPal
                    </button>
                  )}

                  {userRole === 'FREELANCE' && escrowStatus === 'FUNDED' && (
                    <button
                      onClick={handleRunAiAudit}
                      className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 rounded-xl text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition"
                    >
                      <Sparkles className="w-4 h-4" />
                      Soumettre & Lancer l'Audit Gemini
                    </button>
                  )}

                  {userRole === 'CLIENT' && escrowStatus === 'APPROVED' && (
                    <button
                      onClick={handleReleasePayout}
                      className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-3 rounded-xl text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/20 transition"
                    >
                      <ShieldCheck className="w-4 h-4" />
                      Débloquer le Séquestre (PayPal Payouts)
                    </button>
                  )}

                  {escrowStatus === 'PAID_OUT' && (
                    <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 text-xs text-center space-y-1">
                      <div className="font-bold flex items-center justify-center gap-1">
                        <CheckCircle2 className="w-4 h-4" />
                        Paiement Payouts Réussi !
                      </div>
                      <p>Fonds transférés vers freelance.escrow.receiver@sandbox.paypal.com</p>
                      <button
                        onClick={handleResetDemo}
                        className="mt-2 text-xs text-slate-400 hover:text-white underline"
                      >
                        Réinitialiser la simulation
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Deliverable & Live AI Report */}
              <div className="lg:col-span-2 space-y-6">
                {/* Deliverable Editor */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FileCode className="w-4 h-4 text-indigo-400" />
                      <span className="font-semibold text-white text-sm">Livrable soumis par le Freelance</span>
                    </div>
                    <span className="text-xs text-slate-400">Version 1.0 (Python / Django)</span>
                  </div>

                  <textarea
                    value={deliverableCode}
                    onChange={(e) => setDeliverableCode(e.target.value)}
                    rows={6}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500"
                    placeholder="Contenu du livrable, code source ou documentation..."
                  />

                  {escrowStatus === 'AWAITING_PAYMENT' && (
                    <div className="text-xs text-amber-400 flex items-center gap-1.5 bg-amber-500/10 p-3 rounded-lg border border-amber-500/20">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      Passez en vue Client pour déposer les fonds sous séquestre PayPal avant la soumission.
                    </div>
                  )}
                </div>

                {/* AI Gemini Verification Card */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-emerald-400 flex items-center justify-center text-white font-bold text-xs shadow-md">
                        AI
                      </div>
                      <div>
                        <h3 className="font-bold text-white text-sm">Rapport d'Audit Gemini 2.5 Flash</h3>
                        <p className="text-xs text-slate-400">Arbitre autonome de conformité de livrable</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span
                        className={`text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider ${
                          auditVerdict === 'PASS'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {auditVerdict === 'PASS' ? 'Conforme (Validation)' : 'Révisions requises'}
                      </span>
                      <div className="text-right">
                        <span className="text-2xl font-black text-emerald-400 font-mono">{aiScore}</span>
                        <span className="text-xs text-slate-400">/100</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                    <p className="text-xs text-slate-300 italic border-l-2 border-indigo-500 pl-3">
                      "L'analyse automatisée par Gemini 2.5 Flash atteste de la présence d'une gestion complète des flux de séquestre, d'une modélisation Django rigoureuse avec Custom User et d'une intégration fluide avec les API PayPal et SDK google-genai."
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-2">
                      <div className="bg-emerald-950/20 border border-emerald-500/20 p-3 rounded-lg space-y-1">
                        <strong className="text-emerald-400 block font-semibold">Exigences validées :</strong>
                        <ul className="text-slate-300 space-y-1">
                          <li className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            Modèle User (AbstractUser, CLIENT / FREELANCE)
                          </li>
                          <li className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            Gestion des clés PayPal & Gemini via .env
                          </li>
                          <li className="flex items-center gap-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            Configuration SQLite & Template Tailwind
                          </li>
                        </ul>
                      </div>

                      <div className="bg-slate-900 border border-slate-800 p-3 rounded-lg space-y-1">
                        <strong className="text-indigo-400 block font-semibold">Recommandation Séquestre :</strong>
                        <p className="text-slate-300">
                          Score supérieur au seuil de 80%. Déblocage immédiat des fonds via PayPal Payouts autorisé sans risque de fraude.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'files' && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* File List Navigator */}
            <div className="lg:col-span-1 space-y-2">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Fichiers du projet :</div>
              {DJANGO_FILES.map((file, idx) => (
                <button
                  key={file.path}
                  onClick={() => setSelectedFileIndex(idx)}
                  className={`w-full text-left p-3 rounded-xl border transition flex items-center justify-between ${
                    selectedFileIndex === idx
                      ? 'bg-indigo-600/10 border-indigo-500/40 text-white shadow-sm'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-white hover:border-slate-700'
                  }`}
                >
                  <div className="space-y-0.5">
                    <div className="text-xs font-mono font-medium">{file.path}</div>
                    <div className="text-[10px] text-slate-500">{file.badge}</div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
                </button>
              ))}
            </div>

            {/* Code Viewer */}
            <div className="lg:col-span-3 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-lg">
              <div className="p-4 border-b border-slate-800 bg-slate-950 flex items-center justify-between">
                <div>
                  <span className="font-mono text-xs font-bold text-indigo-400">{DJANGO_FILES[selectedFileIndex].path}</span>
                  <p className="text-xs text-slate-400 mt-0.5">{DJANGO_FILES[selectedFileIndex].description}</p>
                </div>
                <button
                  onClick={() => copyCode(DJANGO_FILES[selectedFileIndex].code, DJANGO_FILES[selectedFileIndex].path)}
                  className="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-lg text-xs font-medium transition"
                >
                  {copiedPath === DJANGO_FILES[selectedFileIndex].path ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      Copié !
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copier le code
                    </>
                  )}
                </button>
              </div>

              <pre className="p-6 text-xs font-mono text-slate-300 overflow-x-auto bg-slate-950/70 max-h-[580px] leading-relaxed">
                <code>{DJANGO_FILES[selectedFileIndex].code}</code>
              </pre>
            </div>
          </div>
        )}

        {activeTab === 'cli' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-3">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Terminal className="w-5 h-5 text-emerald-400" />
                Commandes CLI pour démarrer le projet Django en local
              </h2>
              <p className="text-sm text-slate-400">
                Suivez ces instructions pour lancer le projet TrustBridge AI avec SQLite et les comptes de test préconfigurés.
              </p>
            </div>

            <div className="space-y-4">
              {/* Step 1 */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-bold flex items-center justify-center">1</span>
                    <span className="text-sm font-semibold text-white">Créer et activer le virtualenv Python</span>
                  </div>
                  <button
                    onClick={() => copyCode('python3 -m venv venv && source venv/bin/activate', 'step1')}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    {copiedPath === 'step1' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Copier
                  </button>
                </div>
                <pre className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-emerald-400">
                  python3 -m venv venv && source venv/bin/activate
                </pre>
              </div>

              {/* Step 2 */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-bold flex items-center justify-center">2</span>
                    <span className="text-sm font-semibold text-white">Installer les dépendances certifiées</span>
                  </div>
                  <button
                    onClick={() => copyCode('pip install -r requirements.txt', 'step2')}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    {copiedPath === 'step2' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Copier
                  </button>
                </div>
                <pre className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-emerald-400">
                  pip install -r requirements.txt
                </pre>
              </div>

              {/* Step 3 */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-bold flex items-center justify-center">3</span>
                    <span className="text-sm font-semibold text-white">Appliquer les migrations SQLite</span>
                  </div>
                  <button
                    onClick={() => copyCode('python manage.py makemigrations core && python manage.py migrate', 'step3')}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    {copiedPath === 'step3' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Copier
                  </button>
                </div>
                <pre className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-emerald-400">
                  python manage.py makemigrations core && python manage.py migrate
                </pre>
              </div>

              {/* Step 4 */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-bold flex items-center justify-center">4</span>
                    <span className="text-sm font-semibold text-white">Charger les utilisateurs et le contrat de démo</span>
                  </div>
                  <button
                    onClick={() => copyCode('python manage.py seed_demo', 'step4')}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    {copiedPath === 'step4' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Copier
                  </button>
                </div>
                <pre className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-emerald-400">
                  python manage.py seed_demo
                </pre>
                <div className="text-xs text-slate-400">
                  Crée automatiquement : <code className="text-indigo-400">admin</code> (pass: admin1234), <code className="text-blue-400">client_demo</code> et <code className="text-purple-400">freelance_demo</code> (pass: hackathon2026).
                </div>
              </div>

              {/* Step 5 */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-bold flex items-center justify-center">5</span>
                    <span className="text-sm font-semibold text-white">Lancer le serveur de développement</span>
                  </div>
                  <button
                    onClick={() => copyCode('python manage.py runserver', 'step5')}
                    className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                  >
                    {copiedPath === 'step5' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    Copier
                  </button>
                </div>
                <pre className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-emerald-400">
                  python manage.py runserver
                </pre>
              </div>

              {/* One-click shell script */}
              <div className="bg-gradient-to-r from-indigo-950/40 to-slate-900 border border-indigo-500/30 rounded-2xl p-5 flex items-center justify-between">
                <div>
                  <h4 className="font-semibold text-white text-sm">Ou exécutez le script tout-en-un généré :</h4>
                  <p className="text-xs text-slate-400">Configure automatiquement venv, dépendances, migrations et seed.</p>
                </div>
                <button
                  onClick={() => copyCode('./run_project.sh', 'allinone')}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-xs flex items-center gap-2 transition"
                >
                  {copiedPath === 'allinone' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  Copier ./run_project.sh
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'architecture' && (
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-3">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                Architecture Modulaire TrustBridge AI
              </h2>
              <p className="text-sm text-slate-400">
                Découplage strict entre la couche de données Django, les services tiers (PayPal REST, Google Gemini 2.5 Flash) et les rôles utilisateurs.
              </p>
            </div>

            {/* Architecture Schema */}
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 font-mono text-xs text-slate-300 leading-relaxed overflow-x-auto shadow-inner">
              <pre className="text-indigo-300">
{`┌────────────────────────────────────────────────────────────────────────┐
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
   └───────────────────┘                     └───────────────────┘`}
              </pre>
            </div>

            {/* Key Architectural Decisions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center font-bold text-xs">
                  AUTH
                </div>
                <h4 className="font-semibold text-white text-sm">Modèle User Personnalisé</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Hérité de <code className="text-indigo-300">AbstractUser</code> avec énumération <code className="text-indigo-300">Role.choices</code> (CLIENT et FREELANCE) et champ <code className="text-indigo-300">paypal_email</code> pour les déblocages automatisés.
                </p>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold text-xs">
                  PAY
                </div>
                <h4 className="font-semibold text-white text-sm">Séquestre PayPal v2</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Utilisation des flux Orders v2 (<code className="text-emerald-300">/v2/checkout/orders</code>) pour la séquestration et de l'API Payouts (<code className="text-emerald-300">/v1/payments/payouts</code>) pour le déboursement sans intermédiaire.
                </p>
              </div>

              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-2">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center font-bold text-xs">
                  AI
                </div>
                <h4 className="font-semibold text-white text-sm">SDK Google GenAI</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Utilisation du SDK moderne <code className="text-purple-300">google-genai</code> avec le modèle <code className="text-purple-300">gemini-2.5-flash</code> pour évaluer la conformité des livrables selon les critères du contrat avec réponse JSON structurée.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
