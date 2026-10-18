"""
Module dédié à l'intégration de l'API PayPal Sandbox pour TrustBridge AI.

Gère le cycle de vie financier des jalons (Milestones) :
1. get_oauth_token() : Authentification OAuth2 Client Credentials
2. create_milestone_order(milestone) : Création de commande séquestre Orders v2
3. capture_order_payment(order_id) : Capture des fonds validés par le client
4. send_freelance_payout(milestone) : Déblocage automatique des fonds vers le freelance
   via PayPal Payouts v1 (avec déduction de 5% de commission plateforme)
"""

import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Tuple, Optional
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class PayPalAPIError(Exception):
    """Exception personnalisée levée lors d'erreurs d'appels à l'API PayPal."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class PayPalService:
    """
    Service client pour interagir avec les endpoints REST de PayPal Sandbox.
    """
    SANDBOX_BASE_URL = "https://api-m.sandbox.paypal.com"
    LIVE_BASE_URL = "https://api-m.paypal.com"
    PLATFORM_COMMISSION_RATE = Decimal("0.05")  # 5% de commission

    def __init__(self):
        self.mode = getattr(settings, 'PAYPAL_MODE', 'sandbox').lower()
        self.base_url = self.LIVE_BASE_URL if self.mode == 'live' else self.SANDBOX_BASE_URL
        self.client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '').strip()
        self.client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '').strip()

    # ==========================================================================
    # 1. AUTHENTIFICATION OAUTH2
    # ==========================================================================
    def get_oauth_token(self) -> str:
        """
        Récupère un token d'accès Bearer OAuth2 auprès de PayPal Sandbox.
        Endpoint: POST /v1/oauth2/token (avec HTTP Basic Auth client_id:client_secret).
        """
        # Mode hors-ligne / fallback pour tests sans identifiants configurés
        if not self.client_id or not self.client_secret:
            logger.warning(
                "Identifiants PAYPAL_CLIENT_ID ou PAYPAL_CLIENT_SECRET manquants dans settings/.env. "
                "Utilisation du mode simulation Sandbox."
            )
            return "sandbox_mock_token_trustbridge"

        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}

        try:
            logger.info("Demande de token OAuth2 PayPal Sandbox...")
            response = requests.post(
                url,
                auth=(self.client_id, self.client_secret),
                headers=headers,
                data=data,
                timeout=15
            )
            response.raise_for_status()
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                raise PayPalAPIError("Token OAuth2 absent dans la réponse PayPal.")
            logger.info("Token OAuth2 PayPal Sandbox obtenu avec succès.")
            return token
        except requests.HTTPError as http_err:
            error_details = response.json() if 'response' in locals() and response.text else {}
            logger.error(f"Erreur HTTP OAuth2 PayPal [{http_err.response.status_code}]: {error_details}")
            raise PayPalAPIError(
                f"Échec authentification PayPal OAuth2 : {http_err}",
                status_code=http_err.response.status_code if http_err.response else None,
                response_data=error_details
            ) from http_err
        except requests.RequestException as req_err:
            logger.error(f"Erreur réseau lors de l'appel OAuth2 PayPal : {req_err}")
            raise PayPalAPIError(f"Erreur de communication avec PayPal OAuth2 : {req_err}") from req_err

    # ==========================================================================
    # 2. CRÉATION D'ORDRE SÉQUESTRE POUR JALON (ORDERS v2)
    # ==========================================================================
    def create_milestone_order(self, milestone: Any) -> Tuple[str, str]:
        """
        Crée une commande PayPal Orders v2 correspondant au montant du jalon pour le séquestre.
        Endpoint: POST /v2/checkout/orders (intent: CAPTURE).

        :param milestone: Instance de Milestone ou objet duck-typed avec:
                          - id: Identifiant du jalon
                          - amount: Montant décimal ou float
                          - project.currency ou currency: Devise (USD, EUR)
                          - title: Titre du jalon
        :return: Tuple (order_id, approval_url)
        """
        # Extraction sécurisée des données du jalon
        milestone_id = getattr(milestone, 'id', 'demo')
        title = getattr(milestone, 'title', f"Jalon #{milestone_id}")
        amount_val = Decimal(str(getattr(milestone, 'amount', '100.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        project = getattr(milestone, 'project', None)
        currency = getattr(project, 'currency', getattr(milestone, 'currency', 'USD'))

        token = self.get_oauth_token()

        # Fallback pour le hackathon en cas d'absence de clés Sandbox
        if token == "sandbox_mock_token_trustbridge":
            mock_order_id = f"ORDER-SANDBOX-{uuid.uuid4().hex[:8].upper()}"
            mock_approve = f"https://www.sandbox.paypal.com/checkoutnow?token={mock_order_id}"
            logger.info(f"[SIMULATION] Ordre séquestre créé pour Jalon #{milestone_id}: {mock_order_id}")
            return mock_order_id, mock_approve

        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "PayPal-Request-Id": f"order-milestone-{milestone_id}-{uuid.uuid4().hex[:6]}"
        }

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": f"MILESTONE-{milestone_id}",
                    "description": f"TrustBridge Escrow: {title[:120]}",
                    "custom_id": str(milestone_id),
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount_val:.2f}"
                    }
                }
            ],
            "application_context": {
                "brand_name": "TrustBridge AI Escrow",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
                "return_url": "http://localhost:8000/paypal/return/",
                "cancel_url": "http://localhost:8000/paypal/cancel/"
            }
        }

        try:
            logger.info(f"Création d'ordre PayPal Orders v2 pour le jalon #{milestone_id} ({amount_val} {currency})...")
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()

            order_id = data.get("id")
            if not order_id:
                raise PayPalAPIError("L'identifiant d'ordre est manquant dans la réponse PayPal.")

            # Recherche du lien d'approbation 'approve' pour la redirection du client
            approval_url = ""
            for link in data.get("links", []):
                if link.get("rel") == "approve":
                    approval_url = link.get("href")
                    break

            logger.info(f"Ordre PayPal créé avec succès. ID: {order_id}, Approval: {approval_url}")
            return order_id, approval_url

        except requests.HTTPError as http_err:
            error_data = response.json() if 'response' in locals() and response.text else {}
            logger.error(f"Erreur HTTP Orders v2 [{http_err.response.status_code}]: {error_data}")
            raise PayPalAPIError(
                f"Échec de création de l'ordre PayPal : {http_err}",
                status_code=http_err.response.status_code if http_err.response else None,
                response_data=error_data
            ) from http_err
        except requests.RequestException as req_err:
            logger.error(f"Erreur réseau lors de la création d'ordre PayPal : {req_err}")
            raise PayPalAPIError(f"Erreur réseau PayPal Orders v2 : {req_err}") from req_err

    # ==========================================================================
    # 3. CAPTURE DU PAIEMENT SÉQUESTRÉ (ORDERS v2 CAPTURE)
    # ==========================================================================
    def capture_order_payment(self, order_id: str) -> Dict[str, Any]:
        """
        Capture le paiement de la commande PayPal une fois validée par le client.
        Les fonds sont alors verrouillés sur le compte séquestre TrustBridge.
        Endpoint: POST /v2/checkout/orders/{order_id}/capture.

        :param order_id: Identifiant de commande PayPal (ex: 'ORDER-SANDBOX-1234')
        :return: Dictionnaire contenant le statut et l'ID de capture
        """
        if not order_id:
            raise PayPalAPIError("L'ID de commande (order_id) est obligatoire pour la capture.")

        token = self.get_oauth_token()

        # Simulation offline
        if token == "sandbox_mock_token_trustbridge" or order_id.startswith("ORDER-SANDBOX"):
            mock_capture_id = f"CAPTURE-SANDBOX-{uuid.uuid4().hex[:8].upper()}"
            logger.info(f"[SIMULATION] Capture réussie pour la commande {order_id} -> {mock_capture_id}")
            return {
                "status": "COMPLETED",
                "capture_id": mock_capture_id,
                "order_id": order_id
            }

        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "PayPal-Request-Id": f"capture-{order_id}-{uuid.uuid4().hex[:6]}"
        }

        try:
            logger.info(f"Capture des fonds pour la commande PayPal {order_id}...")
            response = requests.post(url, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()

            status = data.get("status")
            capture_id = None

            # Extraction du capture_id dans purchase_units
            purchase_units = data.get("purchase_units", [])
            if purchase_units:
                captures = purchase_units[0].get("payments", {}).get("captures", [])
                if captures:
                    capture_id = captures[0].get("id")

            logger.info(f"Capture confirmée pour l'ordre {order_id} (Statut: {status}, Capture ID: {capture_id})")
            return {
                "status": status,
                "capture_id": capture_id,
                "raw_response": data
            }

        except requests.HTTPError as http_err:
            error_data = response.json() if 'response' in locals() and response.text else {}
            logger.error(f"Erreur HTTP capture PayPal [{http_err.response.status_code}]: {error_data}")
            raise PayPalAPIError(
                f"Échec de capture du paiement PayPal : {http_err}",
                status_code=http_err.response.status_code if http_err.response else None,
                response_data=error_data
            ) from http_err
        except requests.RequestException as req_err:
            logger.error(f"Erreur réseau capture PayPal : {req_err}")
            raise PayPalAPIError(f"Erreur de communication réseau lors de la capture : {req_err}") from req_err

    # ==========================================================================
    # 4. VERSEMENT AUTOMATISÉ AU FREELANCE (PAYOUTS v1)
    # ==========================================================================
    def send_freelance_payout(self, milestone: Any) -> Dict[str, Any]:
        """
        Transfère automatiquement le montant du jalon vers le compte PayPal du freelance
        après prélèvement d'une commission de 5% par TrustBridge AI.
        Endpoint: POST /v1/payments/payouts.

        :param milestone: Instance de Milestone avec relation vers Project et Freelance
        :return: Dictionnaire avec batch_id, net_amount, commission, et statut
        """
        # Extraction du montant et de la devise
        raw_amount = Decimal(str(getattr(milestone, 'amount', '0.00')))
        if raw_amount <= Decimal('0.00'):
            raise PayPalAPIError("Le montant du jalon doit être strictement supérieur à zéro pour un déblocage.")

        # Calcul financier précis (5% commission, 95% net pour le freelance)
        commission = (raw_amount * self.PLATFORM_COMMISSION_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net_payout = (raw_amount - commission).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Récupération du freelance et de son adresse PayPal
        project = getattr(milestone, 'project', None)
        currency = getattr(project, 'currency', getattr(milestone, 'currency', 'USD'))
        
        freelance = getattr(project, 'freelance', None) if project else getattr(milestone, 'freelance', None)
        freelance_email = None
        if freelance:
            freelance_email = getattr(freelance, 'paypal_email', None) or getattr(freelance, 'email', None)

        # Si l'objet est un dict ou passé directement
        if not freelance_email:
            freelance_email = getattr(milestone, 'freelance_paypal_email', None)

        if not freelance_email:
            raise PayPalAPIError(
                f"Aucune adresse PayPal trouvée pour le freelance du jalon #{getattr(milestone, 'id', '?')}."
            )

        milestone_id = getattr(milestone, 'id', 'demo')
        token = self.get_oauth_token()

        # Simulation offline
        if token == "sandbox_mock_token_trustbridge":
            mock_batch_id = f"PAYOUT-BATCH-SANDBOX-{uuid.uuid4().hex[:8].upper()}"
            logger.info(
                f"[SIMULATION] Payout de {net_payout} {currency} (commission {commission}) "
                f"versé à {freelance_email} (Batch: {mock_batch_id})"
            )
            return {
                "batch_id": mock_batch_id,
                "status": "SUCCESS",
                "receiver": freelance_email,
                "gross_amount": f"{raw_amount:.2f}",
                "commission_amount": f"{commission:.2f}",
                "net_amount": f"{net_payout:.2f}",
                "currency": currency
            }

        url = f"{self.base_url}/v1/payments/payouts"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        sender_batch_id = f"TB-MILESTONE-{milestone_id}-{uuid.uuid4().hex[:6]}"
        payload = {
            "sender_batch_header": {
                "sender_batch_id": sender_batch_id,
                "email_subject": "TrustBridge AI : Vos fonds séquestrés sont débloqués !",
                "email_message": (
                    f"Le livrable pour le jalon #{milestone_id} a été validé par l'audit IA. "
                    f"Montant net crédité : {net_payout:.2f} {currency} (Commission plateforme 5% déduite : {commission:.2f} {currency})."
                )
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": f"{net_payout:.2f}",
                        "currency": currency
                    },
                    "note": f"Versement séquestre Jalon #{milestone_id} validé sur TrustBridge AI",
                    "sender_item_id": f"ITEM-MILESTONE-{milestone_id}",
                    "receiver": freelance_email
                }
            ]
        }

        try:
            logger.info(
                f"Envoi Payouts PayPal Sandbox: {net_payout} {currency} vers {freelance_email} "
                f"(Commission 5%: {commission} {currency})..."
            )
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()

            batch_header = data.get("batch_header", {})
            batch_id = batch_header.get("payout_batch_id")
            batch_status = batch_header.get("batch_status")

            logger.info(f"Payout PayPal initié avec succès. Batch ID: {batch_id}, Statut: {batch_status}")
            return {
                "batch_id": batch_id,
                "status": batch_status,
                "receiver": freelance_email,
                "gross_amount": f"{raw_amount:.2f}",
                "commission_amount": f"{commission:.2f}",
                "net_amount": f"{net_payout:.2f}",
                "currency": currency,
                "raw_response": data
            }

        except requests.HTTPError as http_err:
            error_data = response.json() if 'response' in locals() and response.text else {}
            logger.error(f"Erreur HTTP Payouts PayPal [{http_err.response.status_code}]: {error_data}")
            raise PayPalAPIError(
                f"Échec versement Payouts PayPal : {http_err}",
                status_code=http_err.response.status_code if http_err.response else None,
                response_data=error_data
            ) from http_err
        except requests.RequestException as req_err:
            logger.error(f"Erreur réseau Payouts PayPal : {req_err}")
            raise PayPalAPIError(f"Erreur de communication réseau Payouts : {req_err}") from req_err


# ==============================================================================
# FONCTIONS DIRECTES DU MODULE (Interface simplifiée)
# ==============================================================================

_service_instance = PayPalService()


def get_oauth_token() -> str:
    """Récupère le token Bearer OAuth2 Sandbox PayPal."""
    return _service_instance.get_oauth_token()


def create_milestone_order(milestone: Any) -> Tuple[str, str]:
    """Crée une commande PayPal Orders v2 correspondant au montant du jalon."""
    return _service_instance.create_milestone_order(milestone)


def capture_order_payment(order_id: str) -> Dict[str, Any]:
    """Capture le paiement une fois validé par le client."""
    return _service_instance.capture_order_payment(order_id)


def send_freelance_payout(milestone: Any) -> Dict[str, Any]:
    """Transfère le montant du jalon (moins 5% de commission) vers le paypal_email du freelance."""
    return _service_instance.send_freelance_payout(milestone)
