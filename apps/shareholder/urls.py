from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from . import views
from . import mfa

app_name = 'shareholder'


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Shareholder API health check endpoint for App Runner (no auth required)"""
    return Response({
        'status': 'ok',
        'version': '1.0.0',
        'service': 'tableicty Shareholder Portal API'
    })


urlpatterns = [
    # Health check for App Runner (both with and without trailing slash)
    path('health/', health_check, name='health-check'),
    path('health', health_check, name='health-check-no-slash'),
    
    # Authentication endpoints
    path('auth/register/', views.ShareholderRegisterView.as_view(), name='register'),
    path('auth/login/', views.ShareholderLoginView.as_view(), name='login'),
    path('auth/logout/', views.ShareholderLogoutView.as_view(), name='logout'),
    path('auth/refresh/', views.ShareholderTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.current_user_view, name='current_user'),
    
    # Portfolio endpoints
    path('holdings/', views.shareholder_holdings_view, name='holdings'),
    path('summary/', views.shareholder_summary_view, name='summary'),
    
    # Transaction history
    path('transactions/', views.transaction_history_view, name='transactions'),
    
    # Tax documents
    path('tax-documents/', views.tax_documents_view, name='tax_documents'),
    path('tax-documents/<str:doc_id>/download/', views.tax_document_download_view, name='tax_document_download'),
    
    # Certificate conversion requests
    path('certificate-requests/', views.certificate_requests_list_view, name='certificate_requests_list'),
    path('certificate-requests/<uuid:request_id>/download/', views.certificate_pdf_download_view, name='certificate_pdf_download'),
    path('certificate-conversion/', views.certificate_conversion_request_view, name='certificate_conversion'),
    
    # Profile management
    path('profile/', views.profile_management_view, name='profile'),
    
    # MFA (Multi-Factor Authentication) endpoints
    path('auth/mfa/status/', mfa.mfa_status_view, name='mfa_status'),
    path('auth/mfa/setup/', mfa.mfa_setup_view, name='mfa_setup'),
    path('auth/mfa/verify-setup/', mfa.mfa_verify_setup_view, name='mfa_verify_setup'),
    path('auth/mfa/verify/', mfa.mfa_verify_login_view, name='mfa_verify'),
    path('auth/mfa/disable/', mfa.mfa_disable_view, name='mfa_disable'),
    path('auth/mfa/backup-codes/', mfa.mfa_backup_codes_view, name='mfa_backup_codes'),
]
