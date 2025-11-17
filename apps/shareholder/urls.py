from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'shareholder'

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.ShareholderRegisterView.as_view(), name='register'),
    path('auth/login/', views.ShareholderLoginView.as_view(), name='login'),
    path('auth/logout/', views.ShareholderLogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.current_user_view, name='current_user'),
    
    # Portfolio endpoints
    path('holdings/', views.shareholder_holdings_view, name='holdings'),
    path('summary/', views.shareholder_summary_view, name='summary'),
]
