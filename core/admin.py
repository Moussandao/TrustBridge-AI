from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import User, Project, Milestone, Deliverable


# ==============================================================================
# USER ADMIN
# ==============================================================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Administration personnalisée pour le modèle User.
    Met en valeur le rôle (CLIENT / FREELANCE) et l'adresse PayPal Payouts.
    """
    list_display = (
        'username',
        'email',
        'role_badge',
        'paypal_email',
        'is_staff',
        'is_active',
        'created_at'
    )
    list_filter = ('role', 'is_staff', 'is_active', 'created_at')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'paypal_email')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        (_('TrustBridge Escrow & Profil'), {
            'fields': ('role', 'paypal_email', 'bio')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('TrustBridge Escrow & Profil'), {
            'fields': ('role', 'paypal_email', 'bio')
        }),
    )

    @admin.display(description=_('Rôle'), ordering='role')
    def role_badge(self, obj):
        if obj.is_client():
            return format_html(
                '<span style="background-color: #2563eb; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">CLIENT</span>'
            )
        return format_html(
            '<span style="background-color: #7c3aed; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">FREELANCE</span>'
        )


# ==============================================================================
# INLINES
# ==============================================================================

class MilestoneInline(admin.TabularInline):
    """Permet de visualiser et d'ajouter les jalons directement depuis la fiche projet."""
    model = Milestone
    extra = 1
    fields = ('title', 'amount', 'status', 'paypal_order_id', 'paypal_payout_batch_id')
    show_change_link = True


class DeliverableInline(admin.StackedInline):
    """Permet de consulter les livrables et verdicts IA depuis la fiche jalon."""
    model = Deliverable
    extra = 0
    fields = ('submission_text', 'file_url', 'score', 'ai_review_status', 'ai_feedback', 'submitted_at')
    readonly_fields = ('submitted_at',)
    show_change_link = True


# ==============================================================================
# PROJECT ADMIN
# ==============================================================================

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Administration des projets TrustBridge AI.
    Affiche la synthèse financière, le client, le freelance et les statuts globaux.
    """
    list_display = (
        'title',
        'client',
        'freelance',
        'total_amount_display',
        'status_badge',
        'milestones_count_display',
        'created_at'
    )
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('title', 'description', 'client__username', 'freelance__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MilestoneInline]

    actions = ['mark_in_progress', 'mark_completed']

    @admin.display(description=_('Montant Total'), ordering='total_amount')
    def total_amount_display(self, obj):
        return format_html('<strong>{} {}</strong>', obj.total_amount, obj.currency)

    @admin.display(description=_('Jalons'))
    def milestones_count_display(self, obj):
        count = obj.milestones.count()
        return format_html('<span style="font-weight: 600;">{} jalon(s)</span>', count)

    @admin.display(description=_('Statut'), ordering='status')
    def status_badge(self, obj):
        colors = {
            Project.Status.PENDING: '#f59e0b',
            Project.Status.IN_PROGRESS: '#3b82f6',
            Project.Status.COMPLETED: '#10b981',
            Project.Status.CANCELLED: '#ef4444',
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="background-color: {}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.action(description=_("Passer les projets sélectionnés à 'En cours'"))
    def mark_in_progress(self, request, queryset):
        queryset.update(status=Project.Status.IN_PROGRESS)

    @admin.action(description=_("Passer les projets sélectionnés à 'Terminé'"))
    def mark_completed(self, request, queryset):
        queryset.update(status=Project.Status.COMPLETED)


# ==============================================================================
# MILESTONE ADMIN
# ==============================================================================

@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    """
    Administration des jalons (Milestones).
    Permet de suivre le séquestre PayPal Orders v2 et les versements PayPal Payouts.
    """
    list_display = (
        'title',
        'project',
        'amount_display',
        'status_badge',
        'paypal_order_id',
        'paypal_payout_batch_id',
        'created_at'
    )
    list_filter = ('status', 'project__currency', 'created_at')
    search_fields = (
        'title',
        'description',
        'project__title',
        'paypal_order_id',
        'paypal_payout_batch_id'
    )
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DeliverableInline]

    actions = ['mark_as_funded', 'mark_as_approved', 'mark_as_paid']

    @admin.display(description=_('Montant'), ordering='amount')
    def amount_display(self, obj):
        return format_html('<strong>{} {}</strong>', obj.amount, obj.project.currency)

    @admin.display(description=_('Statut Séquestre'), ordering='status')
    def status_badge(self, obj):
        colors = {
            Milestone.Status.LOCKED: '#64748b',
            Milestone.Status.FUNDED: '#3b82f6',
            Milestone.Status.SUBMITTED: '#f59e0b',
            Milestone.Status.APPROVED: '#06b6d4',
            Milestone.Status.PAID: '#10b981',
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="background-color: {}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.action(description=_("Simuler démo : Marquer comme 'Financé' (Fonds séquestrés PayPal)"))
    def mark_as_funded(self, request, queryset):
        queryset.update(status=Milestone.Status.FUNDED)

    @admin.action(description=_("Simuler démo : Marquer comme 'Approuvé' (Audit IA Validé)"))
    def mark_as_approved(self, request, queryset):
        queryset.update(status=Milestone.Status.APPROVED)

    @admin.action(description=_("Simuler démo : Marquer comme 'Payé' (Payout effectué)"))
    def mark_as_paid(self, request, queryset):
        queryset.update(status=Milestone.Status.PAID)


# ==============================================================================
# DELIVERABLE ADMIN
# ==============================================================================

@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    """
    Administration des livrables et des résultats d'audit IA.
    Permet de visualiser le score Gemini et le rapport d'audit lors des démos.
    """
    list_display = (
        'id',
        'milestone',
        'score_display',
        'ai_review_status_badge',
        'file_url_link',
        'submitted_at'
    )
    list_filter = ('ai_review_status', 'submitted_at')
    search_fields = (
        'milestone__title',
        'milestone__project__title',
        'submission_text',
        'ai_feedback'
    )
    readonly_fields = ('submitted_at',)

    @admin.display(description=_('Score IA'), ordering='score')
    def score_display(self, obj):
        if obj.score is None:
            return format_html('<span style="color: #94a3b8;">Non évalué</span>')
        
        color = '#10b981' if obj.score >= 80 else ('#f59e0b' if obj.score >= 50 else '#ef4444')
        return format_html(
            '<span style="font-weight: bold; font-size: 13px; color: {};">{} / 100</span>',
            color,
            obj.score
        )

    @admin.display(description=_('Verdict IA'), ordering='ai_review_status')
    def ai_review_status_badge(self, obj):
        colors = {
            Deliverable.AIReviewStatus.PENDING: '#f59e0b',
            Deliverable.AIReviewStatus.APPROVED: '#10b981',
            Deliverable.AIReviewStatus.REJECTED: '#ef4444',
        }
        color = colors.get(obj.ai_review_status, '#64748b')
        return format_html(
            '<span style="background-color: {}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_ai_review_status_display()
        )

    @admin.display(description=_('Lien Livrable'))
    def file_url_link(self, obj):
        if obj.file_url:
            return format_html('<a href="{}" target="_blank" style="color: #3b82f6; text-decoration: underline;">Voir livrable &rarr;</a>', obj.file_url)
        return format_html('<span style="color: #94a3b8;">Aucun lien</span>')
