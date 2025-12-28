"""
Reusable mixins for multi-tenant data isolation.

These mixins ensure that API views automatically filter querysets
to only show data belonging to the current user's tenant.
"""
from rest_framework.exceptions import PermissionDenied


class TenantQuerySetMixin:
    """
    Mixin for DRF ViewSets that automatically filters queryset by tenant.
    
    Features:
    - Filters queryset to current user's tenant
    - Platform admins can see all tenants (or filter by ?tenant_id=)
    - Automatically sets tenant on object creation
    
    Usage:
        class IssuerViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
            queryset = Issuer.objects.all()
            serializer_class = IssuerSerializer
            
    Requirements:
    - Model must have a 'tenant' ForeignKey field
    - TenantMiddleware must be active (provides request.tenant)
    """
    
    tenant_field = 'tenant'
    allow_platform_admin_cross_tenant = True
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return queryset.none()
        
        role = getattr(self.request, 'tenant_role', None)
        
        if self.allow_platform_admin_cross_tenant and role == 'PLATFORM_ADMIN':
            tenant_id = self.request.query_params.get('tenant_id')
            if tenant_id:
                return queryset.filter(**{f'{self.tenant_field}_id': tenant_id})
            return queryset
        
        tenant = getattr(self.request, 'tenant', None)
        if not tenant:
            return queryset.none()
        
        return queryset.filter(**{self.tenant_field: tenant})
    
    def perform_create(self, serializer):
        """Automatically set tenant on creation."""
        tenant = getattr(self.request, 'tenant', None)
        
        if not tenant:
            role = getattr(self.request, 'tenant_role', None)
            if role == 'PLATFORM_ADMIN':
                tenant_id = self.request.data.get('tenant') or self.request.data.get('tenant_id')
                if not tenant_id:
                    raise PermissionDenied("Platform admins must specify a tenant_id when creating objects.")
                serializer.save()
                return
            raise PermissionDenied("You must belong to a tenant to create objects.")
        
        if '__' in self.tenant_field:
            serializer.save()
        else:
            serializer.save(**{self.tenant_field: tenant})


class ShareholderOwnerQuerySetMixin:
    """
    Mixin for views that should only show a shareholder's own data.
    
    Used for shareholder portal views where users can only see their own
    holdings, transfers, certificates, etc.
    
    Usage:
        class HoldingViewSet(ShareholderOwnerQuerySetMixin, viewsets.ReadOnlyModelViewSet):
            queryset = Holding.objects.all()
            serializer_class = HoldingSerializer
            owner_field = 'shareholder__user'
    """
    
    owner_field = 'shareholder__user'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        user = getattr(self.request, 'user', None)
        if not user or not user.is_authenticated:
            return queryset.none()
        
        role = getattr(self.request, 'tenant_role', None)
        if role in ('PLATFORM_ADMIN', 'TENANT_ADMIN', 'TENANT_STAFF'):
            tenant = getattr(self.request, 'tenant', None)
            if tenant and hasattr(queryset.model, 'tenant'):
                return queryset.filter(tenant=tenant)
            return queryset
        
        return queryset.filter(**{self.owner_field: user})


class TenantCreateMixin:
    """
    Mixin that automatically injects tenant on object creation.
    
    Use this when you need tenant injection but don't want full queryset filtering.
    """
    
    tenant_field = 'tenant'
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        
        if not tenant:
            role = getattr(self.request, 'tenant_role', None)
            if role != 'PLATFORM_ADMIN':
                raise PermissionDenied("You must belong to a tenant to create objects.")
            super().perform_create(serializer)
            return
        
        serializer.save(**{self.tenant_field: tenant})
