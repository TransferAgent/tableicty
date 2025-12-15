"""
Custom JWT token handling for multi-tenant authentication.

Extends SimpleJWT to include:
- tenant_id: UUID of the user's current tenant
- role: User's role within the tenant (PLATFORM_ADMIN, TENANT_ADMIN, TENANT_STAFF, SHAREHOLDER)
- mfa_verified: Whether the user has completed MFA verification
"""
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from apps.core.models import TenantMembership
from django_otp.plugins.otp_totp.models import TOTPDevice


class TenantTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that adds tenant and role claims to tokens.
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        token['email'] = user.email
        token['username'] = user.username
        
        membership = TenantMembership.objects.filter(user=user).first()
        
        if membership:
            token['tenant_id'] = str(membership.tenant.id)
            token['tenant_slug'] = membership.tenant.slug
            token['role'] = membership.role
        else:
            token['tenant_id'] = None
            token['tenant_slug'] = None
            token['role'] = None
        
        has_mfa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
        token['mfa_enabled'] = has_mfa
        token['mfa_verified'] = False
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        has_mfa = TOTPDevice.objects.filter(user=self.user, confirmed=True).exists()
        
        membership = TenantMembership.objects.filter(user=self.user).first()
        
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'username': self.user.username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }
        
        if membership:
            data['tenant'] = {
                'id': str(membership.tenant.id),
                'name': membership.tenant.name,
                'slug': membership.tenant.slug,
            }
            data['role'] = membership.role
        else:
            data['tenant'] = None
            data['role'] = None
        
        data['mfa_required'] = has_mfa
        data['mfa_verified'] = False
        
        return data


class TenantTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view using tenant-aware serializer.
    """
    serializer_class = TenantTokenObtainPairSerializer


def get_tokens_for_user_with_mfa(user, mfa_verified=False):
    """
    Generate tokens for a user with MFA verification status.
    
    Args:
        user: Django User instance
        mfa_verified: Whether MFA has been verified
        
    Returns:
        dict with 'access' and 'refresh' token strings
    """
    refresh = RefreshToken.for_user(user)
    
    refresh['email'] = user.email
    refresh['username'] = user.username
    
    membership = TenantMembership.objects.filter(user=user).first()
    
    if membership:
        refresh['tenant_id'] = str(membership.tenant.id)
        refresh['tenant_slug'] = membership.tenant.slug
        refresh['role'] = membership.role
    else:
        refresh['tenant_id'] = None
        refresh['tenant_slug'] = None
        refresh['role'] = None
    
    has_mfa = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
    refresh['mfa_enabled'] = has_mfa
    refresh['mfa_verified'] = mfa_verified
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


def get_tenant_from_token(token):
    """
    Extract tenant_id from a JWT token.
    
    Args:
        token: Decoded JWT token (dict)
        
    Returns:
        UUID string of tenant_id or None
    """
    return token.get('tenant_id')


def get_role_from_token(token):
    """
    Extract role from a JWT token.
    
    Args:
        token: Decoded JWT token (dict)
        
    Returns:
        Role string or None
    """
    return token.get('role')
