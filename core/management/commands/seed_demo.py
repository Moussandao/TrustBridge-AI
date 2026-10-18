from django.core.management.base import BaseCommand
from core.models import User, Project, Milestone, Deliverable


class Command(BaseCommand):
    help = "Seed initial demo users, project, milestones, and deliverable for TrustBridge AI hackathon demo."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initialisation des données de démo TrustBridge AI..."))

        # 1. Superuser
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@trustbridge.ai",
                "role": User.Role.CLIENT,
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin_user.set_password("admin1234")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Superutilisateur 'admin' créé (mdp: admin1234)."))

        # 2. Client demo user
        client_user, created = User.objects.get_or_create(
            username="client_demo",
            defaults={
                "email": "client@trustbridge.ai",
                "role": User.Role.CLIENT,
                "bio": "Fondateur de FinTech Startup - recherche experts Django & IA."
            }
        )
        if created:
            client_user.set_password("hackathon2026")
            client_user.save()
            self.stdout.write(self.style.SUCCESS("Utilisateur CLIENT 'client_demo' créé (mdp: hackathon2026)."))

        # 3. Freelance demo user
        freelance_user, created = User.objects.get_or_create(
            username="freelance_demo",
            defaults={
                "email": "freelance@trustbridge.ai",
                "role": User.Role.FREELANCE,
                "paypal_email": "freelance.escrow.receiver@sandbox.paypal.com",
                "bio": "Senior Python/Django Architect & LLM Engineer."
            }
        )
        if created:
            freelance_user.set_password("hackathon2026")
            freelance_user.save()
            self.stdout.write(self.style.SUCCESS("Utilisateur FREELANCE 'freelance_demo' créé (mdp: hackathon2026)."))

        # 4. Sample Project
        project, created = Project.objects.get_or_create(
            title="Plateforme Escrow TrustBridge AI & Audit Livrables Gemini",
            client=client_user,
            freelance=freelance_user,
            defaults={
                "description": (
                    "Développement d'un système de séquestre intelligent découpé en jalons (milestones), "
                    "avec blocage des fonds par PayPal Orders v2, audit de conformité automatique par "
                    "l'IA Google Gemini 2.5 Flash et déblocage automatisé via PayPal Payouts."
                ),
                "total_amount": 1500.00,
                "currency": "USD",
                "status": Project.Status.IN_PROGRESS,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Projet #{project.id} '{project.title}' créé."))

            # 5. Milestones
            # Jalon 1 : Payé
            m1 = Milestone.objects.create(
                project=project,
                title="Jalon 1 : Modélisation des données & Architecture Django",
                description="Conception des modèles User (CLIENT/FREELANCE), Project, Milestone et Deliverable.",
                amount=500.00,
                status=Milestone.Status.PAID,
                paypal_order_id="PAYPAL-ORDER-MOCK-101",
                paypal_payout_batch_id="PAYOUT-BATCH-MOCK-001"
            )

            # Jalon 2 : Approuvé (prêt pour payout)
            m2 = Milestone.objects.create(
                project=project,
                title="Jalon 2 : Intégration API PayPal Orders v2 & Payouts",
                description="Service d'émission des ordres de séquestre et déboursement automatique vers le freelance.",
                amount=500.00,
                status=Milestone.Status.APPROVED,
                paypal_order_id="PAYPAL-ORDER-MOCK-102"
            )

            # Livrable du Jalon 2
            Deliverable.objects.create(
                milestone=m2,
                submission_text="""# Livrable Jalon 2 : Service PayPal v2
- Implémentation du service PayPalEscrowService avec gestion de token OAuth2
- Création d'ordres de séquestre via /v2/checkout/orders
- Capture des fonds sous séquestre
- Transfert automatisé des gains via /v1/payments/payouts avec prélèvement de commission""",
                file_url="https://github.com/freelance-demo/trustbridge-api",
                score=94,
                ai_review_status=Deliverable.AIReviewStatus.APPROVED,
                ai_feedback=(
                    "Audit Gemini 2.5 Flash : Conformité validée à 94%. "
                    "Tous les endpoints REST de l'API PayPal Sandbox sont correctement enveloppés avec gestion des erreurs HTTP."
                )
            )

            # Jalon 3 : Fonds sous séquestre actif
            Milestone.objects.create(
                project=project,
                title="Jalon 3 : Arbitre IA Gemini 2.5 Flash & Dashboard",
                description="Interface de suivi en temps réel et pipeline d'audit multimodal.",
                amount=500.00,
                status=Milestone.Status.FUNDED,
                paypal_order_id="PAYPAL-ORDER-MOCK-103"
            )

            self.stdout.write(self.style.SUCCESS("3 jalons (Payé, Approuvé, Financé) et livrable d'évaluation initialisés."))

        self.stdout.write(self.style.SUCCESS("--- Données de démonstration TrustBridge AI prêtes ! ---"))
