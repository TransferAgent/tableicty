from django.urls import path
from . import views

app_name = 'shareholder'

urlpatterns = [
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
    
    # Certificate conversion requests
    path('certificate-conversion/', views.certificate_conversion_request_view, name='certificate_conversion'),
    
    # Profile management
    path('profile/', views.profile_management_view, name='profile'),
]
