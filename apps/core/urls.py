"""
URL configuration for tenant management endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.core.tenant_views import (
    TenantRegistrationView,
    TenantDetailView,
    TenantMembershipViewSet,
    TenantInvitationViewSet,
    validate_invitation,
    accept_invitation,
    current_tenant_view,
    subscription_plans_view,
    billing_status_view,
    create_checkout_session_view,
    create_portal_session_view,
    cancel_subscription_view,
)
from apps.core.webhooks import stripe_webhook

router = DefaultRouter()
router.register(r'members', TenantMembershipViewSet, basename='tenant-members')
router.register(r'invitations', TenantInvitationViewSet, basename='tenant-invitations')

urlpatterns = [
    path('register/', TenantRegistrationView.as_view(), name='tenant-register'),
    path('current/', current_tenant_view, name='current-tenant'),
    path('settings/', TenantDetailView.as_view(), name='tenant-settings'),
    path('subscription-plans/', subscription_plans_view, name='subscription-plans'),
    path('invitations/validate/<str:token>/', validate_invitation, name='validate-invitation'),
    path('invitations/accept/<str:token>/', accept_invitation, name='accept-invitation'),
    path('billing/', billing_status_view, name='billing-status'),
    path('billing/checkout/', create_checkout_session_view, name='billing-checkout'),
    path('billing/portal/', create_portal_session_view, name='billing-portal'),
    path('billing/cancel/', cancel_subscription_view, name='billing-cancel'),
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
    path('', include(router.urls)),
]
