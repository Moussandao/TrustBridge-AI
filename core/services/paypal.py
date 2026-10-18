"""
PayPal Integration Service for TrustBridge AI Escrow Platform.

Handles:
1. OAuth2 Client Credentials Authentication with PayPal REST API.
2. Order creation for client escrow deposit (/v2/checkout/orders).
3. Order capture to securely lock funds in escrow.
4. Instant Payout to freelance's PayPal email upon AI approval (/v1/payments/payouts).
"""

import logging
import uuid
import requests
from django.conf import settings
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PayPalServiceError(Exception):
    """Custom exception raised during PayPal API operations."""
    pass


class PayPalEscrowService:
    def __init__(self):
        self.base_url = getattr(settings, 'PAYPAL_API_BASE_URL', 'https://api-m.sandbox.paypal.com')
        self.client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
        self.mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')

    def get_access_token(self) -> str:
        """
        Retrieves an OAuth2 access token from PayPal REST API.
        """
        if not self.client_id or not self.client_secret:
            logger.warning("PayPal credentials not configured. Using sandbox fallback mode.")
            return "mock-sandbox-token"

        url = f"{self.base_url}/v1/oauth2/token"
        headers = {
            "Accept": "application/json",
            "Accept-Language": "en_US",
        }
        data = {"grant_type": "client_credentials"}

        try:
            response = requests.post(
                url,
                auth=(self.client_id, self.client_secret),
                headers=headers,
                data=data,
                timeout=15
            )
            response.raise_for_status()
            payload = response.json()
            return payload.get("access_token", "")
        except requests.RequestException as e:
            logger.error(f"Failed to obtain PayPal OAuth token: {e}")
            raise PayPalServiceError(f"Erreur d'authentification PayPal: {str(e)}")

    def create_escrow_order(
        self,
        contract_id: int,
        title: str,
        amount: float,
        currency: str = "EUR",
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a PayPal Order for the Client to fund the escrow contract.
        """
        token = self.get_access_token()

        if token == "mock-sandbox-token":
            # Deterministic mock response for offline hackathon testing
            mock_id = f"PAYPAL-ORDER-MOCK-{uuid.uuid4().hex[:8].upper()}"
            return {
                "id": mock_id,
                "status": "CREATED",
                "approval_url": f"https://www.sandbox.paypal.com/checkoutnow?token={mock_id}",
                "amount": f"{amount:.2f}",
                "currency": currency
            }

        url = f"{self.base_url}/v2/checkout/orders"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": f"CONTRACT-{contract_id}",
                    "description": f"TrustBridge Escrow: {title[:120]}",
                    "custom_id": str(contract_id),
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}"
                    }
                }
            ],
            "application_context": {
                "brand_name": "TrustBridge AI Escrow",
                "landing_page": "BILLING",
                "user_action": "PAY_NOW",
                "return_url": return_url or "http://localhost:8000/contracts/paypal-callback/",
                "cancel_url": cancel_url or "http://localhost:8000/contracts/paypal-cancel/"
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            order_data = response.json()
            
            # Extract approval link for client redirect
            approval_url = ""
            for link in order_data.get("links", []):
                if link.get("rel") == "approve":
                    approval_url = link.get("href")
                    break

            return {
                "id": order_data.get("id"),
                "status": order_data.get("status"),
                "approval_url": approval_url,
                "raw": order_data
            }
        except requests.RequestException as e:
            logger.error(f"Failed to create PayPal escrow order: {e}")
            raise PayPalServiceError(f"Échec création ordre séquestre PayPal: {str(e)}")

    def capture_escrow_order(self, order_id: str) -> Dict[str, Any]:
        """
        Captures authorized payment from the client, locking it into the platform escrow.
        """
        token = self.get_access_token()

        if token == "mock-sandbox-token" or order_id.startswith("PAYPAL-ORDER-MOCK"):
            return {
                "status": "COMPLETED",
                "capture_id": f"CAPTURE-MOCK-{uuid.uuid4().hex[:8].upper()}",
                "order_id": order_id
            }

        url = f"{self.base_url}/v2/checkout/orders/{order_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        try:
            response = requests.post(url, headers=headers, timeout=20)
            response.raise_for_status()
            capture_data = response.json()
            
            # Retrieve primary capture ID
            capture_id = ""
            purchase_units = capture_data.get("purchase_units", [])
            if purchase_units:
                captures = purchase_units[0].get("payments", {}).get("captures", [])
                if captures:
                    capture_id = captures[0].get("id")

            return {
                "status": capture_data.get("status"),
                "capture_id": capture_id,
                "raw": capture_data
            }
        except requests.RequestException as e:
            logger.error(f"Failed to capture PayPal escrow order {order_id}: {e}")
            raise PayPalServiceError(f"Échec capture des fonds séquestre: {str(e)}")

    def release_escrow_to_freelance(
        self,
        contract_id: int,
        freelance_paypal_email: str,
        amount: float,
        currency: str = "EUR",
        note: str = "Paiement TrustBridge AI libéré après validation de conformité"
    ) -> Dict[str, Any]:
        """
        Disburses escrowed funds directly to the Freelance via PayPal Payouts API.
        Triggered when Gemini AI deliverable verification passes and is approved.
        """
        if not freelance_paypal_email:
            raise PayPalServiceError("L'adresse email PayPal du freelance est requise pour le déblocage des fonds.")

        token = self.get_access_token()

        if token == "mock-sandbox-token":
            return {
                "batch_id": f"PAYOUT-BATCH-MOCK-{uuid.uuid4().hex[:8].upper()}",
                "status": "SUCCESS",
                "receiver": freelance_paypal_email,
                "amount": f"{amount:.2f}",
                "currency": currency
            }

        url = f"{self.base_url}/v1/payments/payouts"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        
        sender_batch_id = f"TB-PAYOUT-{contract_id}-{uuid.uuid4().hex[:6]}"
        payload = {
            "sender_batch_header": {
                "sender_batch_id": sender_batch_id,
                "email_subject": "TrustBridge AI : Vos fonds séquestrés sont libérés !",
                "email_message": note
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": currency
                    },
                    "note": f"Mission #{contract_id} validée avec succès sur TrustBridge AI",
                    "sender_item_id": f"ITEM-{contract_id}",
                    "receiver": freelance_paypal_email
                }
            ]
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            payout_data = response.json()
            batch_header = payout_data.get("batch_header", {})
            return {
                "batch_id": batch_header.get("payout_batch_id"),
                "status": batch_header.get("batch_status"),
                "receiver": freelance_paypal_email,
                "raw": payout_data
            }
        except requests.RequestException as e:
            logger.error(f"Failed to execute PayPal payout to freelance {freelance_paypal_email}: {e}")
            raise PayPalServiceError(f"Échec versement PayPal Payouts au freelance: {str(e)}")
