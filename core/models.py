from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """
    Modèle Utilisateur personnalisé pour TrustBridge AI.
    Prend en charge deux rôles fondamentaux : CLIENT et FREELANCE,
    ainsi que l'adresse email PayPal requise pour les versements via Payouts.
    """
    class Role(models.TextChoices):
        CLIENT = 'CLIENT', _('Client (Donneur d\'ordre)')
        FREELANCE = 'FREELANCE', _('Freelance (Prestataire)')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.FREELANCE,
        help_text=_('Rôle de l\'utilisateur sur la plateforme TrustBridge AI.')
    )

    paypal_email = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        help_text=_('Adresse email associée au compte PayPal pour recevoir les paiements (séquestre/payouts).')
    )

    bio = models.TextField(
        blank=True,
        null=True,
        help_text=_('Présentation courte du profil ou de l\'entreprise.')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_client(self) -> bool:
        """Retourne True si l'utilisateur est un Client."""
        return self.role == self.Role.CLIENT

    def is_freelance(self) -> bool:
        """Retourne True si l'utilisateur est un Freelance."""
        return self.role == self.Role.FREELANCE

    def __str__(self) -> str:
        role_label = self.get_role_display()
        return f"{self.username} ({role_label})"


class Project(models.Model):
    """
    Projet / Contrat cadre entre un Client et un Freelance.
    Regroupe l'ensemble des jalons (Milestones) et définit le montant total.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        IN_PROGRESS = 'IN_PROGRESS', _('En cours')
        COMPLETED = 'COMPLETED', _('Terminé')
        CANCELLED = 'CANCELLED', _('Annulé')

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects_as_client',
        limit_choices_to={'role': User.Role.CLIENT},
        help_text=_('Client qui finance le projet.')
    )
    freelance = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects_as_freelance',
        limit_choices_to={'role': User.Role.FREELANCE},
        help_text=_('Freelance chargé de la réalisation.')
    )

    title = models.CharField(max_length=255, help_text=_('Titre du projet'))
    description = models.TextField(blank=True, help_text=_('Description et cahier des charges du projet'))

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_('Montant total cumulé du projet.')
    )
    currency = models.CharField(max_length=3, default='USD', help_text=_('Devise (ex: USD, EUR).'))

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=_('Statut global d\'avancement du projet.')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Projet')
        verbose_name_plural = _('Projets')

    @property
    def milestones_count(self) -> int:
        """Retourne le nombre total de jalons associés."""
        return self.milestones.count()

    @property
    def funded_amount(self) -> float:
        """Montant total actuellement sécurisé en séquestre (FUNDED ou au-delà)."""
        funded_statuses = [
            Milestone.Status.FUNDED,
            Milestone.Status.SUBMITTED,
            Milestone.Status.APPROVED,
            Milestone.Status.PAID
        ]
        return sum(
            m.amount for m in self.milestones.filter(status__in=funded_statuses)
        )

    def is_fully_paid(self) -> bool:
        """Vérifie si tous les jalons sont payés."""
        milestones = self.milestones.all()
        if not milestones.exists():
            return False
        return all(m.status == Milestone.Status.PAID for m in milestones)

    def __str__(self) -> str:
        return f"{self.title} ({self.client.username} -> {self.freelance.username}) [{self.get_status_display()}]"


class Milestone(models.Model):
    """
    Jalon individuel d'un projet.
    Chaque jalon est séquestré via PayPal Orders v2 et débloqué via PayPal Payouts.
    """
    class Status(models.TextChoices):
        LOCKED = 'LOCKED', _('Verrouillé (Non financé)')
        FUNDED = 'FUNDED', _('Financé (Séquestre PayPal actif)')
        SUBMITTED = 'SUBMITTED', _('Livrable soumis (Audit en cours)')
        APPROVED = 'APPROVED', _('Approuvé par l\'IA & Client')
        PAID = 'PAID', _('Payé (Fonds débloqués au freelance)')

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='milestones',
        help_text=_('Projet parent associé à ce jalon.')
    )

    title = models.CharField(max_length=255, help_text=_('Titre ou objectif du jalon'))
    description = models.TextField(blank=True, help_text=_('Spécifications et critères attendus pour ce jalon'))

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_('Montant sécurisé pour ce jalon.')
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.LOCKED,
        help_text=_('Statut du jalon dans le cycle de séquestre.')
    )

    # Identifiants de suivi PayPal
    paypal_order_id = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text=_('Identifiant de la commande PayPal Orders v2 (Séquestre client).')
    )
    paypal_payout_batch_id = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text=_('Identifiant du lot de versement PayPal Payouts vers le freelance.')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _('Jalon (Milestone)')
        verbose_name_plural = _('Jalons (Milestones)')

    @property
    def latest_deliverable(self):
        """Retourne le dernier livrable soumis pour ce jalon."""
        return self.deliverables.order_by('-submitted_at').first()

    def is_funded(self) -> bool:
        """Vérifie si les fonds sont effectivement séquestrés."""
        return self.status in [
            self.Status.FUNDED,
            self.Status.SUBMITTED,
            self.Status.APPROVED,
            self.Status.PAID
        ]

    def is_paid(self) -> bool:
        """Vérifie si le jalon a été reversé au freelance."""
        return self.status == self.Status.PAID

    def __str__(self) -> str:
        return f"{self.project.title} - {self.title} ({self.amount} {self.project.currency}) [{self.get_status_display()}]"


class Deliverable(models.Model):
    """
    Livrable soumis par le Freelance pour un Jalon spécifique.
    Fait l'objet d'un audit de conformité automatique par Google Gemini.
    """
    class AIReviewStatus(models.TextChoices):
        PENDING = 'PENDING', _('En attente d\'audit IA')
        APPROVED = 'APPROVED', _('Validé par l\'IA (Conforme)')
        REJECTED = 'REJECTED', _('Rejeté / Révisions nécessaires')

    milestone = models.ForeignKey(
        Milestone,
        on_delete=models.CASCADE,
        related_name='deliverables',
        help_text=_('Jalon auquel se rattache ce livrable.')
    )

    submission_text = models.TextField(
        help_text=_('Description technique, extraits de code ou notes d\'implémentation.')
    )

    file_url = models.URLField(
        blank=True,
        null=True,
        help_text=_('Lien externe vers le code source ou fichier (GitHub, GitLab, Google Drive, etc.).')
    )

    ai_review_status = models.CharField(
        max_length=20,
        choices=AIReviewStatus.choices,
        default=AIReviewStatus.PENDING,
        help_text=_('Verdict d\'évaluation émis par Google Gemini.')
    )

    ai_feedback = models.TextField(
        blank=True,
        null=True,
        help_text=_('Rapport détaillé généré par l\'IA (points forts, faiblesses, recommandations).')
    )

    score = models.IntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Score global de conformité de 0 à 100 calculé par l\'IA.')
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('Date et heure de la soumission du livrable.')
    )

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = _('Livrable')
        verbose_name_plural = _('Livrables')

    def is_reviewed(self) -> bool:
        """Indique si l'audit IA a été réalisé."""
        return self.ai_review_status != self.AIReviewStatus.PENDING

    def is_passing(self) -> bool:
        """Retourne True si le score est supérieur ou égal au seuil de conformité (80/100)."""
        return self.ai_review_status == self.AIReviewStatus.APPROVED and (self.score is not None and self.score >= 80)

    def __str__(self) -> str:
        score_display = f"{self.score}/100" if self.score is not None else "En attente"
        return f"Livrable #{self.id} pour {self.milestone.title} ({self.get_ai_review_status_display()} - {score_display})"
