"""
Custom middleware for tableicty Transfer Agent platform.
"""
from django.http import HttpResponse
from django.utils.functional import SimpleLazyObject
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging

logger = logging.getLogger(__name__)


def get_tenant_from_user(user):
    """
    Get tenant from authenticated user via TenantMembership lookup.
    
    Uses database lookup to verify tenant membership - more secure than
    trusting JWT claims directly.
    
    Returns Tenant instance or None.
    """
    if not user or not user.is_authenticated:
        return None
    
    from apps.core.models import TenantMembership
    
    membership = TenantMembership.objects.filter(user=user).select_related('tenant').first()
    if membership:
        return membership.tenant
    return None


def get_role_from_user(user):
    """
    Get role from authenticated user via TenantMembership lookup.
    
    Uses database lookup to verify role - more secure than
    trusting JWT claims directly.
    
    Returns role string or None.
    """
    if not user or not user.is_authenticated:
        return None
    
    from apps.core.models import TenantMembership
    
    membership = TenantMembership.objects.filter(user=user).first()
    if membership:
        return membership.role
    return None


def get_mfa_verified_from_token(request):
    """
    Get MFA verification status from JWT token.
    
    This claim is trusted because it's set server-side during MFA verification.
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    
    if not auth_header.startswith('Bearer '):
        return False
    
    try:
        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(auth_header.split(' ', 1)[1])
        return validated_token.get('mfa_verified', False)
    except (InvalidToken, TokenError):
        return False


class TenantMiddleware:
    """
    Middleware to inject tenant context into request.
    
    Uses authenticated user from SimpleJWT and verifies membership against
    database to prevent JWT claim spoofing.
    
    Adds to request:
    - request.tenant: Tenant instance (lazy loaded from DB)
    - request.tenant_role: User's role verified from DB
    - request.mfa_verified: Whether MFA was verified (from JWT claim)
    
    This middleware should run AFTER AuthenticationMiddleware.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        def get_tenant():
            user = getattr(request, 'user', None)
            return get_tenant_from_user(user)
        
        def get_role():
            user = getattr(request, 'user', None)
            return get_role_from_user(user)
        
        request.tenant = SimpleLazyObject(get_tenant)
        request.tenant_role = SimpleLazyObject(get_role)
        request.mfa_verified = get_mfa_verified_from_token(request)
        
        return self.get_response(request)


class HealthCheckMiddleware:
    """
    Middleware to handle health check endpoints for App Runner.
    
    This middleware short-circuits health check requests and returns an
    immediate 200 OK response BEFORE SecurityMiddleware can redirect to HTTPS.
    
    App Runner's health checker uses plain HTTP and doesn't follow redirects,
    so we need to respond before any redirect logic runs.
    """
    
    HEALTH_CHECK_PATHS = (
        '/api/v1/shareholder/health',
        '/api/v1/shareholder/health/',
        '/api/v1/health',
        '/api/v1/health/',
    )
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path in self.HEALTH_CHECK_PATHS and request.method == 'GET':
            return HttpResponse("OK", content_type="text/plain", status=200)
        
        return self.get_response(request)
