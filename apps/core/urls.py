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
)

router = DefaultRouter()
router.register(r'members', TenantMembershipViewSet, basename='tenant-members')
router.register(r'invitations', TenantInvitationViewSet, basename='tenant-invitations')

urlpatterns = [
    path('register/', TenantRegistrationView.as_view(), name='tenant-register'),
    path('current/', current_tenant_view, name='current-tenant'),
    path('settings/', TenantDetailView.as_view(), name='tenant-settings'),
    path('invitations/validate/<str:token>/', validate_invitation, name='validate-invitation'),
    path('invitations/accept/<str:token>/', accept_invitation, name='accept-invitation'),
    path('', include(router.urls)),
]
