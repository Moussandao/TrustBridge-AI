"""
Couche logique métier et présentation pour TrustBridge AI.

Comprend :
- Dashboard unifié et réactif aux rôles (Client vs Freelance)
- Endpoints PayPal Smart Buttons v2 (createOrder & onApprove capture)
- Soumission des livrables et audit automatique Gemini 1.5/2.5 Flash
- Déblocage automatique des fonds Payouts
- Vue Webhook PayPal (/webhooks/paypal/) pour PAYMENT.CAPTURE.COMPLETED
- Outil de bascule rapide de profil (Demo User Switcher) pour les jurys
"""

import json
import logging
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import User, Project, Milestone, Deliverable
from .services.paypal_service import (
    PayPalService,
    PayPalAPIError,
    create_milestone_order,
    capture_order_payment,
    send_freelance_payout,
)
from .services.ai_service import analyze_deliverable, AIServiceError

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. TABLEAU DE BORD CLIENT & FREELANCE
# ==============================================================================

def dashboard_view(request):
    """
    Tableau de bord dynamique TrustBridge AI :
    - Rôle CLIENT : Vue d'ensemble des projets, boutons de paiement PayPal Smart Buttons,
      visualisation des rapports d'audit Gemini et bouton de libération Payouts.
    - Rôle FREELANCE : Jalons assignés, formulaire de soumission de livrable avec audit immédiat,
      historique des audits et confirmations de versements.
    """
    # Si l'utilisateur n'est pas connecté, connecte automatiquement un compte de démo
    if not request.user.is_authenticated:
        demo_client = User.objects.filter(role=User.Role.CLIENT).first()
        if demo_client:
            login(request, demo_client)
        else:
            return redirect('login')

    user = request.user

    if user.is_client():
        projects = (
            Project.objects.filter(client=user)
            .prefetch_related('milestones__deliverables')
            .order_by('-created_at')
        )
    else:
        projects = (
            Project.objects.filter(freelance=user)
            .prefetch_related('milestones__deliverables')
            .order_by('-created_at')
        )

    # Statistiques globales pour la barre de synthèse KPI
    all_milestones = Milestone.objects.filter(
        project__in=projects
    )

    stats = {
        'total_escrow_locked': sum(
            m.amount for m in all_milestones.filter(status=Milestone.Status.FUNDED)
        ),
        'total_paid_out': sum(
            m.amount for m in all_milestones.filter(status=Milestone.Status.PAID)
        ),
        'pending_audits': all_milestones.filter(status=Milestone.Status.SUBMITTED).count(),
        'approved_count': all_milestones.filter(status=Milestone.Status.APPROVED).count(),
    }

    # Liste des freelances et clients de test pour le sélecteur démo
    demo_clients = User.objects.filter(role=User.Role.CLIENT)
    demo_freelances = User.objects.filter(role=User.Role.FREELANCE)

    context = {
        'projects': projects,
        'stats': stats,
        'user_role': user.get_role_display(),
        'is_client': user.is_client(),
        'is_freelance': user.is_freelance(),
        'paypal_client_id': getattr(settings, 'PAYPAL_CLIENT_ID', 'test') or 'test',
        'paypal_mode': getattr(settings, 'PAYPAL_MODE', 'sandbox'),
        'gemini_model': getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
        'demo_clients': demo_clients,
        'demo_freelances': demo_freelances,
    }

    return render(request, 'core/dashboard.html', context)


# ==============================================================================
# 2. SOUMISSION DE LIVRABLE & AUDIT IA (FREELANCE)
# ==============================================================================

@login_required
@require_POST
def submit_deliverable_view(request, milestone_id):
    """
    Traitement de la soumission d'un livrable par le freelance.
    Déclenche automatiquement l'évaluation de conformité via Google Gemini.
    """
    milestone = get_object_or_404(Milestone, id=milestone_id)

    # Vérification des autorisations
    if request.user != milestone.project.freelance and not request.user.is_staff:
        messages.error(request, "Seul le freelance assigné à ce projet peut soumettre un livrable.")
        return redirect('dashboard')

    if milestone.status not in [Milestone.Status.FUNDED, Milestone.Status.SUBMITTED]:
        messages.warning(
            request,
            f"Impossible de soumettre : le jalon doit être financé (statut actuel : {milestone.get_status_display()})."
        )
        return redirect('dashboard')

    submission_text = request.POST.get('submission_text', '').strip()
    file_url = request.POST.get('file_url', '').strip()

    if not submission_text:
        messages.error(request, "Veuillez fournir le contenu ou le descriptif technique de votre livrable.")
        return redirect('dashboard')

    # 1. Appel du service IA Gemini
    try:
        audit_result = analyze_deliverable(
            milestone_description=milestone.description or milestone.title,
            deliverable_content=submission_text
        )
    except AIServiceError as e:
        logger.error(f"Erreur lors de l'audit IA du livrable #{milestone.id}: {e}")
        messages.error(request, f"L'arbitre IA a rencontré un incident : {e}")
        return redirect('dashboard')

    score = int(audit_result.get('score', 75))
    is_approved = bool(audit_result.get('approved', False))
    summary = audit_result.get('summary', '')
    feedback = audit_result.get('feedback', '')

    full_ai_feedback = f"{summary}\n\n{feedback}".strip()

    # 2. Enregistrement en base de données
    deliverable = Deliverable.objects.create(
        milestone=milestone,
        submission_text=submission_text,
        file_url=file_url,
        score=score,
        ai_review_status=(
            Deliverable.AIReviewStatus.APPROVED
            if is_approved else
            Deliverable.AIReviewStatus.REJECTED
        ),
        ai_feedback=full_ai_feedback
    )

    # 3. Transition de statut du Jalon
    if is_approved:
        milestone.status = Milestone.Status.APPROVED
        messages.success(
            request,
            f"🎉 Audit IA Gemini Validé avec succès ! Score : {score}/100. "
            "Le client peut maintenant autoriser le versement PayPal Payouts."
        )
    else:
        milestone.status = Milestone.Status.SUBMITTED
        messages.warning(
            request,
            f"⚠️ Audit IA Gemini : Révisions requises (Score : {score}/100). Consultez les remarques de l'IA ci-dessous."
        )

    milestone.save()
    return redirect('dashboard')


# ==============================================================================
# 3. ENDPOINTS AJAX PAYPAL SMART BUTTONS (CLIENT)
# ==============================================================================

@login_required
@require_POST
def create_paypal_order_ajax(request, milestone_id):
    """
    Endpoint appelé par la fonction createOrder() du SDK JavaScript PayPal Smart Buttons.
    Génère l'ordre Orders v2 et renvoie l'orderID au navigateur client.
    """
    milestone = get_object_or_404(Milestone, id=milestone_id, project__client=request.user)

    try:
        order_id, approve_url = create_milestone_order(milestone)
        milestone.paypal_order_id = order_id
        milestone.save()

        return JsonResponse({
            'orderID': order_id,
            'approvalUrl': approve_url,
            'amount': str(milestone.amount),
            'currency': milestone.project.currency
        })
    except PayPalAPIError as e:
        logger.error(f"Échec création ordre PayPal pour jalon #{milestone_id}: {e}")
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def capture_paypal_order_ajax(request, milestone_id):
    """
    Endpoint appelé par onApprove() du SDK JavaScript PayPal Smart Buttons.
    Capture les fonds autorisés et passe le jalon à FUNDED (Fonds sous séquestre).
    """
    milestone = get_object_or_404(Milestone, id=milestone_id, project__client=request.user)

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except ValueError:
        body = {}

    order_id = body.get('orderID') or milestone.paypal_order_id
    if not order_id:
        return JsonResponse({'error': "Identifiant de commande orderID manquant."}, status=400)

    try:
        capture_result = capture_order_payment(order_id)
        milestone.status = Milestone.Status.FUNDED
        milestone.paypal_order_id = order_id
        milestone.save()

        # Met à jour le projet parent si nécessaire
        if milestone.project.status == Project.Status.PENDING:
            milestone.project.status = Project.Status.IN_PROGRESS
            milestone.project.save()

        return JsonResponse({
            'status': 'COMPLETED',
            'captureID': capture_result.get('capture_id'),
            'milestoneStatus': milestone.get_status_display()
        })
    except PayPalAPIError as e:
        logger.error(f"Échec capture PayPal pour jalon #{milestone_id}: {e}")
        return JsonResponse({'error': str(e)}, status=400)


# ==============================================================================
# 4. LIBÉRATION DES FONDS PAYPAL PAYOUTS (CLIENT OU ADMIN)
# ==============================================================================

@login_required
@require_POST
def release_milestone_payout(request, milestone_id):
    """
    Déclenche le versement des fonds sécurisés vers l'adresse PayPal du freelance
    via l'API PayPal Payouts (déduction automatique des 5% de commission).
    """
    milestone = get_object_or_404(Milestone, id=milestone_id)

    if request.user != milestone.project.client and not request.user.is_staff:
        messages.error(request, "Seul le client commanditaire peut débloquer le séquestre.")
        return redirect('dashboard')

    if milestone.status != Milestone.Status.APPROVED:
        messages.warning(
            request,
            f"Le jalon doit être approuvé avant libération (statut actuel : {milestone.get_status_display()})."
        )
        return redirect('dashboard')

    try:
        payout_data = send_freelance_payout(milestone)
        milestone.status = Milestone.Status.PAID
        milestone.paypal_payout_batch_id = payout_data.get('batch_id')
        milestone.save()

        # Si tous les jalons du projet sont payés, passe le projet à COMPLETED
        if milestone.project.is_fully_paid():
            milestone.project.status = Project.Status.COMPLETED
            milestone.project.save()

        net = payout_data.get('net_amount', milestone.amount)
        cur = payout_data.get('currency', milestone.project.currency)
        rec = payout_data.get('receiver', 'freelance')

        messages.success(
            request,
            f"💸 Versement PayPal Payouts réussi ! {net} {cur} crédités sur le compte PayPal de {rec} "
            f"(Commission plateforme 5% déduite : {payout_data.get('commission_amount')} {cur})."
        )
    except PayPalAPIError as e:
        logger.error(f"Erreur Payout PayPal pour jalon #{milestone_id}: {e}")
        messages.error(request, f"Échec du déblocage PayPal Payouts : {e}")

    return redirect('dashboard')


# ==============================================================================
# 5. VUE WEBHOOK PAYPAL (/webhooks/paypal/)
# ==============================================================================

@csrf_exempt
@require_POST
def paypal_webhook_view(request):
    """
    Point de terminaison Webhook PayPal pour écouter les événements asynchrones.
    Traite notamment 'PAYMENT.CAPTURE.COMPLETED' et 'CHECKOUT.ORDER.COMPLETED'.
    Passe automatiquement le jalon correspondant au statut 'FUNDED'.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as e:
        logger.warning(f"Webhook PayPal reçu avec un corps non JSON valide: {e}")
        return HttpResponseBadRequest("Payload JSON invalide")

    event_type = payload.get('event_type')
    resource = payload.get('resource', {})
    logger.info(f"Webhook PayPal reçu : événement '{event_type}'")

    if event_type in ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.COMPLETED']:
        # 1. Recherche par custom_id ou order_id
        order_id = resource.get('id')
        custom_id = resource.get('custom_id')

        # Si le custom_id est dans purchase_units
        if not custom_id and 'purchase_units' in resource:
            pu = resource['purchase_units']
            if pu and len(pu) > 0:
                custom_id = pu[0].get('custom_id')

        milestone = None

        # Recherche prioritaire par ID de jalon (stocké dans custom_id)
        if custom_id and str(custom_id).isdigit():
            milestone = Milestone.objects.filter(id=int(custom_id)).first()

        # Recherche secondaire par paypal_order_id
        if not milestone and order_id:
            milestone = Milestone.objects.filter(paypal_order_id=order_id).first()

        if milestone:
            if milestone.status in [Milestone.Status.LOCKED, Milestone.Status.SUBMITTED]:
                milestone.status = Milestone.Status.FUNDED
                milestone.save()

                if milestone.project.status == Project.Status.PENDING:
                    milestone.project.status = Project.Status.IN_PROGRESS
                    milestone.project.save()

                logger.info(
                    f"Webhook PayPal : Jalon #{milestone.id} ('{milestone.title}') "
                    f"automatiquement passé au statut FUNDED."
                )
        else:
            logger.warning(f"Webhook PayPal : Aucun jalon trouvé pour order_id='{order_id}', custom_id='{custom_id}'")

    # Toujours retourner un statut 200 à PayPal pour acquitter la réception
    return HttpResponse(status=200)


# ==============================================================================
# 6. UTILITAIRE DE BASCULE RAPIDE DE COMPTE DÉMO (HACKATHON)
# ==============================================================================

def switch_demo_user(request, user_id):
    """
    Permet aux jurys et testeurs de basculer instantanément entre le rôle
    Client et le rôle Freelance sans retaper de mot de passe.
    """
    target_user = get_object_or_404(User, id=user_id)
    login(request, target_user)
    messages.info(
        request,
        f"Session active : {target_user.username} ({target_user.get_role_display()})"
    )
    return redirect('dashboard')
