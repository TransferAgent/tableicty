"""
Role-based permission classes for multi-tenant access control.

Permission hierarchy:
1. PLATFORM_ADMIN - Full access to all tenants (Tableicty staff)
2. TENANT_ADMIN - Full access to their tenant
3. TENANT_STAFF - Limited admin access to their tenant
4. SHAREHOLDER - View-only access to their own holdings
"""
from rest_framework import permissions
from apps.core.models import TenantMembership


class IsPlatformAdmin(permissions.BasePermission):
    """
    Permission for Tableicty platform administrators.
    
    Platform admins can access data across all tenants.
    """
    message = "Platform administrator access required."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = getattr(request, 'tenant_role', None)
        if role == 'PLATFORM_ADMIN':
            return True
        
        return TenantMembership.objects.filter(
            user=request.user,
            role='PLATFORM_ADMIN'
        ).exists()


class IsTenantAdmin(permissions.BasePermission):
    """
    Permission for tenant administrators.
    
    Tenant admins have full access to their tenant's data.
    Also grants access to platform admins.
    """
    message = "Tenant administrator access required."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = getattr(request, 'tenant_role', None)
        if role in ('PLATFORM_ADMIN', 'TENANT_ADMIN'):
            return True
        
        return TenantMembership.objects.filter(
            user=request.user,
            role__in=['PLATFORM_ADMIN', 'TENANT_ADMIN']
        ).exists()


class IsTenantStaff(permissions.BasePermission):
    """
    Permission for tenant staff.
    
    Tenant staff have limited admin access to their tenant's data.
    Also grants access to tenant admins and platform admins.
    """
    message = "Tenant staff access required."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = getattr(request, 'tenant_role', None)
        if role in ('PLATFORM_ADMIN', 'TENANT_ADMIN', 'TENANT_STAFF'):
            return True
        
        return TenantMembership.objects.filter(
            user=request.user,
            role__in=['PLATFORM_ADMIN', 'TENANT_ADMIN', 'TENANT_STAFF']
        ).exists()


class IsTenantMember(permissions.BasePermission):
    """
    Permission for any tenant member.
    
    Grants access to all authenticated users who belong to a tenant.
    """
    message = "You must be a member of a tenant to access this resource."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        tenant = getattr(request, 'tenant', None)
        if tenant:
            return True
        
        return TenantMembership.objects.filter(user=request.user).exists()


class IsSameTenant(permissions.BasePermission):
    """
    Object-level permission to ensure users can only access their tenant's objects.
    
    The object must have a 'tenant' attribute.
    Platform admins can access objects from any tenant.
    """
    message = "You can only access objects within your tenant."
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = getattr(request, 'tenant_role', None)
        if role == 'PLATFORM_ADMIN':
            return True
        
        request_tenant = getattr(request, 'tenant', None)
        object_tenant = getattr(obj, 'tenant', None)
        
        if request_tenant and object_tenant:
            if hasattr(request_tenant, 'id') and hasattr(object_tenant, 'id'):
                return str(request_tenant.id) == str(object_tenant.id)
        
        return False


class IsMFAVerifiedOrExempt(permissions.BasePermission):
    """
    Permission that requires MFA verification if user has MFA enabled.
    
    Allows access if:
    - User does not have MFA enabled
    - User has MFA enabled AND has verified for this session
    
    Denies access if:
    - User has MFA enabled but hasn't verified
    """
    message = "MFA verification required."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        has_mfa = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()
        
        if not has_mfa:
            return True
        
        mfa_verified = getattr(request, 'mfa_verified', False)
        return mfa_verified


class TenantScopedPermission(permissions.BasePermission):
    """
    Combined permission for tenant-scoped access.
    
    Checks:
    1. User is authenticated
    2. User belongs to a tenant
    3. For object access, user's tenant matches object's tenant
    """
    message = "Access denied."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = getattr(request, 'tenant_role', None)
        if role == 'PLATFORM_ADMIN':
            return True
        
        tenant = getattr(request, 'tenant', None)
        return tenant is not None
    
    def has_object_permission(self, request, view, obj):
        role = getattr(request, 'tenant_role', None)
        if role == 'PLATFORM_ADMIN':
            return True
        
        request_tenant = getattr(request, 'tenant', None)
        object_tenant = getattr(obj, 'tenant', None)
        
        if not request_tenant or not object_tenant:
            return False
        
        return str(request_tenant.id) == str(object_tenant.id)


class CanManageTenant(permissions.BasePermission):
    """
    Permission for managing tenant settings and configuration.
    
    Only PLATFORM_ADMIN and TENANT_ADMIN can manage tenants.
    """
    message = "Tenant management access required."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = getattr(request, 'tenant_role', None)
        return role in ('PLATFORM_ADMIN', 'TENANT_ADMIN')


class CanManageUsers(permissions.BasePermission):
    """
    Permission for managing tenant users and invitations.
    
    PLATFORM_ADMIN, TENANT_ADMIN, and TENANT_STAFF can manage users.
    """
    message = "User management access required."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = getattr(request, 'tenant_role', None)
        return role in ('PLATFORM_ADMIN', 'TENANT_ADMIN', 'TENANT_STAFF')


class CanProcessTransfers(permissions.BasePermission):
    """
    Permission for processing stock transfers.
    
    PLATFORM_ADMIN and TENANT_ADMIN can process transfers.
    TENANT_STAFF can initiate but not approve transfers.
    """
    message = "Transfer processing access required."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        role = getattr(request, 'tenant_role', None)
        
        if request.method in permissions.SAFE_METHODS:
            return role in ('PLATFORM_ADMIN', 'TENANT_ADMIN', 'TENANT_STAFF')
        
        return role in ('PLATFORM_ADMIN', 'TENANT_ADMIN')
