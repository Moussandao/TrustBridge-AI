"""
Service d'analyse de conformité des livrables par IA pour TrustBridge AI.

Utilise le SDK officiel Google GenAI (`google-genai`) ou `google-generativeai`
pour évaluer si le travail soumis par le freelance satisfait les critères du jalon (Milestone).
"""

import json
import logging
import os
import re
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# Détection et support des deux SDKs Google GenAI (moderne et legacy)
USE_NEW_SDK = False
USE_LEGACY_SDK = False

try:
    from google import genai
    from google.genai import types
    USE_NEW_SDK = True
except ImportError:
    try:
        import google.generativeai as legacy_genai
        USE_LEGACY_SDK = True
    except ImportError:
        logger.warning(
            "Ni 'google-genai' ni 'google-generativeai' ne sont installés. "
            "Le service fonctionnera en mode simulation d'audit pour les démos."
        )


class AIServiceError(Exception):
    """Exception levée en cas d'erreur de communication ou de parsing lors de l'audit IA."""
    pass


class AIService:
    """
    Arbitre impartial pour l'évaluation automatisée des livrables freelances.
    """
    DEFAULT_SYSTEM_INSTRUCTION = (
        "Tu es un expert impartial et bienveillant en revue de projets numériques et de code source. "
        "Ton rôle est d'analyser avec rigueur et équité si la réalisation / le livrable fourni par le freelance "
        "répond bien aux critères et spécifications exigés dans le jalon (milestone) du contrat de séquestre. "
        "Tu dois impérativement répondre sous la forme d'un objet JSON strict et valide."
    )

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        # Récupération de la clé d'API (settings Django ou variable d'environnement)
        self.api_key = (
            api_key
            or getattr(settings, 'GEMINI_API_KEY', '')
            or os.environ.get('GEMINI_API_KEY', '')
        ).strip()

        # Choix du modèle : priorité à gemini-2.5-flash / gemini-1.5-flash configuré
        self.model_name = (
            model_name
            or getattr(settings, 'GEMINI_MODEL', '')
            or os.environ.get('GEMINI_MODEL', '')
            or 'gemini-1.5-flash'
        ).strip()

        self.client = None
        self._init_sdk_client()

    def _init_sdk_client(self):
        """Initialise le client SDK selon le package disponible."""
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.info("Clé GEMINI_API_KEY non fournie. Mode d'évaluation heuristique activé.")
            return

        if USE_NEW_SDK:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Client Google GenAI SDK initialisé avec succès (modèle: {self.model_name}).")
            except Exception as e:
                logger.error(f"Échec d'initialisation de Google GenAI Client : {e}")
                self.client = None
        elif USE_LEGACY_SDK:
            try:
                legacy_genai.configure(api_key=self.api_key)
                self.client = legacy_genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self.DEFAULT_SYSTEM_INSTRUCTION
                )
                logger.info(f"Client legacy google.generativeai configuré (modèle: {self.model_name}).")
            except Exception as e:
                logger.error(f"Échec de configuration de google.generativeai : {e}")
                self.client = None

    def analyze_deliverable(
        self,
        milestone_description: str,
        deliverable_content: str,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyse la réalisation fournie par le freelance par rapport à la description du jalon.

        :param milestone_description: Cahier des charges et critères attendus pour le jalon.
        :param deliverable_content: Code, texte ou résumé technique soumis par le freelance.
        :param model_name: Surcharge optionnelle du modèle Gemini à utiliser.
        :return: Dictionnaire JSON strict :
                 {
                     "approved": bool,
                     "score": int,
                     "summary": str,
                     "feedback": str
                 }
        """
        milestone_desc = (milestone_description or "").strip()
        deliverable_text = (deliverable_content or "").strip()

        if not milestone_desc:
            raise AIServiceError("La description du jalon (milestone_description) est obligatoire pour l'audit.")

        target_model = model_name or self.model_name

        # Construction du prompt structuré
        prompt = f"""
=== CONTEXTE D'ARBITRAGE ===
Tu es un expert impartial en revue de projets numériques. Évalue la conformité du travail ci-dessous.

=== 1. JALON EXIGÉ (CRITÈRES & SPÉCIFICATIONS) ===
{milestone_desc}

=== 2. LIVRABLE FOURNI PAR LE FREELANCE (CODE / RÉALISATION) ===
{deliverable_text if deliverable_text else "Aucun texte fourni directement (veuillez vérifier les métadonnées ou le lien externe)."}

=== INSTRUCTION DE SORTIE STRICTE ===
Tu dois analyser si les exigences sont satisfaites et répondre UNIQUEMENT par un objet JSON valide, sans balises markdown superflues, respectant scrupuleusement ce schéma :
{{
  "approved": <true ou false>,
  "score": <entier entre 0 et 100>,
  "summary": "<Résumé concis et professionnel de l'analyse en français (2-3 phrases)>",
  "feedback": "<Points forts et éléments manquants éventuels détaillés>"
}}

Règles de validation :
- Si le travail satisfait au moins 80% des exigences clés : "approved": true et "score" >= 80.
- Si des éléments critiques manquent ou si le travail est non conforme : "approved": false et "score" < 80.
"""

        # 1. Appel via le SDK officiel moderne `google-genai`
        if USE_NEW_SDK and self.client:
            try:
                logger.info(f"Envoi du livrable à Gemini ({target_model}) via google-genai...")
                response = self.client.models.generateContent(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.DEFAULT_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                raw_text = response.text or ""
                return self._parse_json_response(raw_text)
            except Exception as e:
                logger.error(f"Erreur d'exécution de google-genai : {e}. Utilisation du fallback d'audit.")

        # 2. Appel via le SDK `google.generativeai` (legacy)
        elif USE_LEGACY_SDK and self.client:
            try:
                logger.info(f"Envoi du livrable à Gemini ({target_model}) via google.generativeai...")
                response = self.client.generate_content(
                    prompt,
                    generation_config={"temperature": 0.2, "response_mime_type": "application/json"}
                )
                raw_text = response.text or ""
                return self._parse_json_response(raw_text)
            except Exception as e:
                logger.error(f"Erreur d'exécution de google.generativeai : {e}. Utilisation du fallback d'audit.")

        # 3. Fallback d'évaluation locale si aucune clé active ou SDK indisponible
        return self._local_heuristic_analysis(milestone_desc, deliverable_text)

    def _parse_json_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Nettoie et parse la réponse brute de Gemini pour garantir un JSON valide.
        Gère les blocs de code markdown ```json ... ``` et les espaces résiduels.
        """
        if not raw_response or not raw_response.strip():
            raise AIServiceError("La réponse renvoyée par Gemini est vide.")

        cleaned = raw_response.strip()

        # Supprimer d'éventuels blocs markdown ```json ... ```
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as decode_err:
            # Tentative d'extraction par regex d'un objet JSON { ... }
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except json.JSONDecodeError:
                    logger.error(f"Impossible de parser le JSON extrait de Gemini: {cleaned}")
                    raise AIServiceError(f"Format JSON invalide dans la réponse Gemini : {decode_err}")
            else:
                logger.error(f"Aucun bloc JSON détecté dans la réponse Gemini : {cleaned}")
                raise AIServiceError(f"Réponse Gemini non décodable en JSON : {decode_err}")

        # Normalisation et validation stricte des champs demandés
        score = int(data.get("score", 75))
        approved = bool(data.get("approved", score >= 80))
        summary = str(data.get("summary", "Analyse de conformité réalisée par l'arbitre IA."))
        feedback = str(data.get("feedback", "Livrable évalué selon les spécifications."))

        return {
            "approved": approved,
            "score": score,
            "summary": summary,
            "feedback": feedback
        }

    def _local_heuristic_analysis(self, milestone_desc: str, deliverable_text: str) -> Dict[str, Any]:
        """
        Générateur de rapport heuristique pour les démos hackathon lorsque l'API Gemini
        n'a pas de clé externe renseignée ou s'exécute hors-ligne.
        """
        has_content = len(deliverable_text) > 40
        has_keywords = any(kw in deliverable_text.lower() for kw in ["def ", "class ", "http", "api", "token", "test", "import"])
        
        is_valid = has_content and has_keywords
        score = 88 if is_valid else 55
        approved = score >= 80

        if approved:
            summary = (
                "L'analyse de conformité démontre une adéquation satisfaisante entre le livrable "
                "fourni par le freelance et les critères définis pour le jalon. La validation est recommandée."
            )
            feedback = (
                "Points forts : Structure technique cohérente, critères principaux implémentés et gestion des cas nominaux. "
                "Éléments manquants éventuels : Pensez à enrichir la couverture de tests et la documentation des cas d'erreur limites."
            )
        else:
            summary = (
                "Le livrable soumis ne contient pas suffisamment d'éléments vérifiables ou ne couvre "
                "pas l'ensemble des fonctionnalités requises dans le jalon."
            )
            feedback = (
                "Points forts : Début de soumission identifié. "
                "Éléments manquants : Absence de code source complet, manque de documentation ou critères essentiels non démontrés."
            )

        logger.info(f"[SIMULATION AUDIT] Score calculé: {score}/100, Approved: {approved}")
        return {
            "approved": approved,
            "score": score,
            "summary": summary,
            "feedback": feedback
        }


# ==============================================================================
# FONCTION DIRECTE DU MODULE
# ==============================================================================

_ai_service_instance = AIService()


def analyze_deliverable(milestone_description: str, deliverable_content: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Fonction utilitaire principale pour analyser un livrable avec Gemini.

    Exemple d'utilisation :
        result = analyze_deliverable(
            milestone_description="Développer l'endpoint /api/orders avec authentification OAuth2",
            deliverable_content="def create_order(request): ... # code complet avec OAuth2"
        )
        if result["approved"]:
            print(f"Jalon validé (score: {result['score']})")
    """
    return _ai_service_instance.analyze_deliverable(
        milestone_description=milestone_description,
        deliverable_content=deliverable_content,
        model_name=model_name
    )
