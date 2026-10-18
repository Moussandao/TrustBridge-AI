from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Dashboard principal (Rôles Client / Freelance)
    path('', views.dashboard_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Actions Jalons (Milestones) & Séquestre PayPal
    path('milestones/<int:milestone_id>/submit/', views.submit_deliverable_view, name='submit_deliverable'),
    path('milestones/<int:milestone_id>/release/', views.release_milestone_payout, name='release_milestone_payout'),

    # Endpoints AJAX PayPal Smart Buttons (JS SDK)
    path('api/milestones/<int:milestone_id>/create-order/', views.create_paypal_order_ajax, name='create_paypal_order_ajax'),
    path('api/milestones/<int:milestone_id>/capture-order/', views.capture_paypal_order_ajax, name='capture_paypal_order_ajax'),

    # Webhook PayPal asynchrone (PAYMENT.CAPTURE.COMPLETED)
    path('webhooks/paypal/', views.paypal_webhook_view, name='paypal_webhook'),

    # Utilitaire de démonstration hackathon (Bascule Client / Freelance instantanée)
    path('demo/switch/<int:user_id>/', views.switch_demo_user, name='switch_demo_user'),

    # Authentification standard
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='dashboard'), name='logout'),
]
