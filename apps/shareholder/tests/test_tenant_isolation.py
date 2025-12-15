"""
Comprehensive tests for multi-tenant data isolation.

Tests cover:
- Tenant-scoped data access
- Cross-tenant access prevention
- Role-based permission enforcement
- TenantMiddleware functionality
- TenantQuerySetMixin behavior
- JWT tenant claims
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth.models import User
from django.http import HttpRequest
from rest_framework.test import APIClient
from rest_framework import status
from apps.core.models import (
    Tenant, TenantMembership, SubscriptionPlan, Subscription,
    Issuer, Shareholder, Holding, SecurityClass, Transfer
)
from apps.core.middleware import TenantMiddleware, get_tenant_from_user, get_role_from_user
from apps.core.permissions import (
    IsPlatformAdmin, IsTenantAdmin, IsTenantStaff, IsTenantMember,
    IsSameTenant, IsMFAVerifiedOrExempt, TenantScopedPermission,
    CanManageTenant, CanManageUsers, CanProcessTransfers
)
from apps.core.mixins import TenantQuerySetMixin, ShareholderOwnerQuerySetMixin
from datetime import date
from decimal import Decimal


@pytest.fixture
def subscription_plan(db):
    """Create a subscription plan."""
    return SubscriptionPlan.objects.create(
        name='Starter',
        slug='starter',
        tier='STARTER',
        price_monthly=Decimal('49.00'),
        price_yearly=Decimal('490.00'),
        max_shareholders=100,
        max_transfers_per_month=10,
        max_users=3
    )


@pytest.fixture
def tenant_a(db, subscription_plan):
    """Create tenant A with subscription."""
    tenant = Tenant.objects.create(
        name='Company A',
        slug='company-a',
        primary_email='admin@company-a.com',
        status='ACTIVE'
    )
    Subscription.objects.create(
        tenant=tenant,
        plan=subscription_plan,
        status='ACTIVE'
    )
    return tenant


@pytest.fixture
def tenant_b(db, subscription_plan):
    """Create tenant B with subscription."""
    tenant = Tenant.objects.create(
        name='Company B',
        slug='company-b',
        primary_email='admin@company-b.com',
        status='ACTIVE'
    )
    Subscription.objects.create(
        tenant=tenant,
        plan=subscription_plan,
        status='ACTIVE'
    )
    return tenant


@pytest.fixture
def admin_user_a(db, tenant_a):
    """Create admin user for tenant A."""
    user = User.objects.create_user(
        username='admin_a@company-a.com',
        email='admin_a@company-a.com',
        password='testpass123'
    )
    TenantMembership.objects.create(
        tenant=tenant_a,
        user=user,
        role='TENANT_ADMIN'
    )
    return user


@pytest.fixture
def admin_user_b(db, tenant_b):
    """Create admin user for tenant B."""
    user = User.objects.create_user(
        username='admin_b@company-b.com',
        email='admin_b@company-b.com',
        password='testpass123'
    )
    TenantMembership.objects.create(
        tenant=tenant_b,
        user=user,
        role='TENANT_ADMIN'
    )
    return user


@pytest.fixture
def platform_admin(db, tenant_a):
    """Create platform admin user."""
    user = User.objects.create_user(
        username='platform@tableicty.com',
        email='platform@tableicty.com',
        password='testpass123'
    )
    TenantMembership.objects.create(
        tenant=tenant_a,
        user=user,
        role='PLATFORM_ADMIN'
    )
    return user


@pytest.fixture
def shareholder_a(db, tenant_a):
    """Create shareholder in tenant A."""
    user = User.objects.create_user(
        username='investor_a@example.com',
        email='investor_a@example.com',
        password='testpass123'
    )
    shareholder = Shareholder.objects.create(
        tenant=tenant_a,
        user=user,
        email='investor_a@example.com',
        first_name='Alice',
        last_name='Investor',
        account_type='INDIVIDUAL',
        address_line1='123 A Street',
        city='Boston',
        state='MA',
        zip_code='02101',
        country='US'
    )
    TenantMembership.objects.create(
        tenant=tenant_a,
        user=user,
        role='SHAREHOLDER'
    )
    return shareholder


@pytest.fixture
def shareholder_b(db, tenant_b):
    """Create shareholder in tenant B."""
    user = User.objects.create_user(
        username='investor_b@example.com',
        email='investor_b@example.com',
        password='testpass123'
    )
    shareholder = Shareholder.objects.create(
        tenant=tenant_b,
        user=user,
        email='investor_b@example.com',
        first_name='Bob',
        last_name='Investor',
        account_type='INDIVIDUAL',
        address_line1='456 B Avenue',
        city='Chicago',
        state='IL',
        zip_code='60601',
        country='US'
    )
    TenantMembership.objects.create(
        tenant=tenant_b,
        user=user,
        role='SHAREHOLDER'
    )
    return shareholder


@pytest.fixture
def issuer_a(db, tenant_a):
    """Create issuer in tenant A."""
    return Issuer.objects.create(
        tenant=tenant_a,
        company_name='Company A Inc',
        ticker_symbol='CMPA',
        total_authorized_shares=Decimal('10000000'),
        par_value=Decimal('0.001'),
        incorporation_state='DE',
        incorporation_country='US',
        agreement_start_date=date.today(),
        annual_fee=Decimal('5000.00')
    )


@pytest.fixture
def issuer_b(db, tenant_b):
    """Create issuer in tenant B."""
    return Issuer.objects.create(
        tenant=tenant_b,
        company_name='Company B Corp',
        ticker_symbol='CMPB',
        total_authorized_shares=Decimal('5000000'),
        par_value=Decimal('0.001'),
        incorporation_state='NY',
        incorporation_country='US',
        agreement_start_date=date.today(),
        annual_fee=Decimal('3000.00')
    )


@pytest.mark.django_db
class TestTenantMiddleware:
    """Tests for TenantMiddleware functionality."""
    
    def test_middleware_initializes_correctly(self):
        """Middleware initializes with get_response callable."""
        mock_get_response = Mock(return_value=Mock())
        middleware = TenantMiddleware(mock_get_response)
        assert middleware.get_response == mock_get_response
    
    def test_middleware_sets_tenant_attributes_on_request(self):
        """Middleware adds tenant, tenant_role, and mfa_verified to request."""
        mock_get_response = Mock(return_value=Mock())
        middleware = TenantMiddleware(mock_get_response)
        
        request = HttpRequest()
        request.META = {}
        
        middleware(request)
        
        assert hasattr(request, 'tenant')
        assert hasattr(request, 'tenant_role')
        assert hasattr(request, 'mfa_verified')
    
    def test_middleware_handles_missing_auth_header(self):
        """Middleware handles requests without Authorization header."""
        mock_get_response = Mock(return_value=Mock())
        middleware = TenantMiddleware(mock_get_response)
        
        request = HttpRequest()
        request.META = {}
        
        middleware(request)
        
        assert request.mfa_verified is False
    
    def test_middleware_handles_invalid_bearer_token(self):
        """Middleware handles invalid Bearer token gracefully."""
        mock_get_response = Mock(return_value=Mock())
        middleware = TenantMiddleware(mock_get_response)
        
        request = HttpRequest()
        request.META = {'HTTP_AUTHORIZATION': 'Bearer invalid_token'}
        
        middleware(request)
        
        assert request.mfa_verified is False


@pytest.mark.django_db
class TestRoleBasedPermissions:
    """Tests for role-based permission classes."""
    
    def test_is_platform_admin_rejects_unauthenticated(self):
        """IsPlatformAdmin denies unauthenticated users."""
        permission = IsPlatformAdmin()
        request = Mock()
        request.user = None
        
        assert permission.has_permission(request, None) is False
    
    def test_is_platform_admin_rejects_non_admin(self, admin_user_a, tenant_a):
        """IsPlatformAdmin denies non-platform admin users."""
        permission = IsPlatformAdmin()
        request = Mock()
        request.user = admin_user_a
        request.tenant_role = 'TENANT_ADMIN'
        
        assert permission.has_permission(request, None) is False
    
    def test_is_platform_admin_allows_platform_admin(self, platform_admin):
        """IsPlatformAdmin allows platform admin users."""
        permission = IsPlatformAdmin()
        request = Mock()
        request.user = platform_admin
        request.tenant_role = 'PLATFORM_ADMIN'
        
        assert permission.has_permission(request, None) is True
    
    def test_is_tenant_admin_allows_tenant_admin(self, admin_user_a, tenant_a):
        """IsTenantAdmin allows tenant admin users."""
        permission = IsTenantAdmin()
        request = Mock()
        request.user = admin_user_a
        request.tenant_role = 'TENANT_ADMIN'
        
        assert permission.has_permission(request, None) is True
    
    def test_is_tenant_admin_rejects_shareholder(self, shareholder_a):
        """IsTenantAdmin denies shareholder users."""
        permission = IsTenantAdmin()
        request = Mock()
        request.user = shareholder_a.user
        request.tenant_role = 'SHAREHOLDER'
        
        assert permission.has_permission(request, None) is False
    
    def test_is_tenant_staff_allows_staff(self, tenant_a):
        """IsTenantStaff allows staff users."""
        user = User.objects.create_user(
            username='staff@company-a.com',
            email='staff@company-a.com',
            password='testpass123'
        )
        TenantMembership.objects.create(
            tenant=tenant_a,
            user=user,
            role='TENANT_STAFF'
        )
        
        permission = IsTenantStaff()
        request = Mock()
        request.user = user
        request.tenant_role = 'TENANT_STAFF'
        
        assert permission.has_permission(request, None) is True
    
    def test_is_tenant_member_allows_any_member(self, shareholder_a, tenant_a):
        """IsTenantMember allows any authenticated tenant member."""
        permission = IsTenantMember()
        request = Mock()
        request.user = shareholder_a.user
        request.tenant = tenant_a
        
        assert permission.has_permission(request, None) is True
    
    def test_is_tenant_member_rejects_non_member(self):
        """IsTenantMember denies users not belonging to a tenant."""
        user = User.objects.create_user(
            username='orphan@example.com',
            email='orphan@example.com',
            password='testpass123'
        )
        
        permission = IsTenantMember()
        request = Mock()
        request.user = user
        request.tenant = None
        
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestObjectLevelPermissions:
    """Tests for object-level tenant permission."""
    
    def test_is_same_tenant_allows_same_tenant(self, admin_user_a, tenant_a, issuer_a):
        """IsSameTenant allows access when tenant matches."""
        permission = IsSameTenant()
        request = Mock()
        request.user = admin_user_a
        request.tenant = tenant_a
        request.tenant_role = 'TENANT_ADMIN'
        
        assert permission.has_object_permission(request, None, issuer_a) is True
    
    def test_is_same_tenant_denies_different_tenant(self, admin_user_a, tenant_a, issuer_b):
        """IsSameTenant denies access when tenant doesn't match."""
        permission = IsSameTenant()
        request = Mock()
        request.user = admin_user_a
        request.tenant = tenant_a
        request.tenant_role = 'TENANT_ADMIN'
        
        assert permission.has_object_permission(request, None, issuer_b) is False
    
    def test_is_same_tenant_allows_platform_admin_any_tenant(self, platform_admin, issuer_b):
        """IsSameTenant allows platform admin access to any tenant's objects."""
        permission = IsSameTenant()
        request = Mock()
        request.user = platform_admin
        request.tenant_role = 'PLATFORM_ADMIN'
        
        assert permission.has_object_permission(request, None, issuer_b) is True
    
    def test_tenant_scoped_permission_has_permission(self, admin_user_a, tenant_a):
        """TenantScopedPermission.has_permission validates tenant membership."""
        permission = TenantScopedPermission()
        request = Mock()
        request.user = admin_user_a
        request.tenant = tenant_a
        request.tenant_role = 'TENANT_ADMIN'
        
        assert permission.has_permission(request, None) is True
    
    def test_tenant_scoped_permission_denies_no_tenant(self, admin_user_a):
        """TenantScopedPermission.has_permission denies users without tenant."""
        permission = TenantScopedPermission()
        request = Mock()
        request.user = admin_user_a
        request.tenant = None
        request.tenant_role = None
        
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestFunctionalPermissions:
    """Tests for functional permission classes."""
    
    def test_can_manage_tenant_allows_admin(self, admin_user_a, tenant_a):
        """CanManageTenant allows tenant admin."""
        permission = CanManageTenant()
        request = Mock()
        request.user = admin_user_a
        request.tenant_role = 'TENANT_ADMIN'
        
        assert permission.has_permission(request, None) is True
    
    def test_can_manage_tenant_denies_staff(self, tenant_a):
        """CanManageTenant denies staff."""
        user = User.objects.create_user(
            username='staff@company-a.com',
            email='staff@company-a.com',
            password='testpass123'
        )
        TenantMembership.objects.create(
            tenant=tenant_a,
            user=user,
            role='TENANT_STAFF'
        )
        
        permission = CanManageTenant()
        request = Mock()
        request.user = user
        request.tenant_role = 'TENANT_STAFF'
        
        assert permission.has_permission(request, None) is False
    
    def test_can_manage_users_allows_staff(self, tenant_a):
        """CanManageUsers allows staff to manage users."""
        user = User.objects.create_user(
            username='staff@company-a.com',
            email='staff@company-a.com',
            password='testpass123'
        )
        TenantMembership.objects.create(
            tenant=tenant_a,
            user=user,
            role='TENANT_STAFF'
        )
        
        permission = CanManageUsers()
        request = Mock()
        request.user = user
        request.tenant_role = 'TENANT_STAFF'
        
        assert permission.has_permission(request, None) is True
    
    def test_can_process_transfers_allows_admin_writes(self, admin_user_a):
        """CanProcessTransfers allows admin for write operations."""
        permission = CanProcessTransfers()
        request = Mock()
        request.user = admin_user_a
        request.tenant_role = 'TENANT_ADMIN'
        request.method = 'POST'
        
        assert permission.has_permission(request, None) is True
    
    def test_can_process_transfers_allows_staff_reads(self, tenant_a):
        """CanProcessTransfers allows staff for read operations."""
        user = User.objects.create_user(
            username='staff@company-a.com',
            email='staff@company-a.com',
            password='testpass123'
        )
        TenantMembership.objects.create(
            tenant=tenant_a,
            user=user,
            role='TENANT_STAFF'
        )
        
        permission = CanProcessTransfers()
        request = Mock()
        request.user = user
        request.tenant_role = 'TENANT_STAFF'
        request.method = 'GET'
        
        assert permission.has_permission(request, None) is True
    
    def test_can_process_transfers_denies_staff_writes(self, tenant_a):
        """CanProcessTransfers denies staff for write operations."""
        user = User.objects.create_user(
            username='staff2@company-a.com',
            email='staff2@company-a.com',
            password='testpass123'
        )
        TenantMembership.objects.create(
            tenant=tenant_a,
            user=user,
            role='TENANT_STAFF'
        )
        
        permission = CanProcessTransfers()
        request = Mock()
        request.user = user
        request.tenant_role = 'TENANT_STAFF'
        request.method = 'POST'
        
        assert permission.has_permission(request, None) is False


@pytest.mark.django_db
class TestMFAPermissions:
    """Tests for MFA-related permissions."""
    
    def test_mfa_verified_or_exempt_allows_no_mfa(self, admin_user_a):
        """IsMFAVerifiedOrExempt allows users without MFA configured."""
        permission = IsMFAVerifiedOrExempt()
        request = Mock()
        request.user = admin_user_a
        request.mfa_verified = False
        
        assert permission.has_permission(request, None) is True
    
    def test_mfa_verified_or_exempt_denies_unverified_with_mfa(self, admin_user_a):
        """IsMFAVerifiedOrExempt denies users with MFA who haven't verified."""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        TOTPDevice.objects.create(
            user=admin_user_a,
            name='test-device',
            confirmed=True
        )
        
        permission = IsMFAVerifiedOrExempt()
        request = Mock()
        request.user = admin_user_a
        request.mfa_verified = False
        
        assert permission.has_permission(request, None) is False
    
    def test_mfa_verified_or_exempt_allows_verified(self, admin_user_a):
        """IsMFAVerifiedOrExempt allows users with verified MFA."""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        
        TOTPDevice.objects.create(
            user=admin_user_a,
            name='test-device',
            confirmed=True
        )
        
        permission = IsMFAVerifiedOrExempt()
        request = Mock()
        request.user = admin_user_a
        request.mfa_verified = True
        
        assert permission.has_permission(request, None) is True


@pytest.mark.django_db
class TestCrossTenantDataIsolation:
    """Integration tests for cross-tenant data isolation."""
    
    def test_tenant_a_cannot_see_tenant_b_issuers(self, tenant_a, tenant_b, issuer_a, issuer_b):
        """Tenant A's issuers don't include Tenant B's issuers."""
        tenant_a_issuers = Issuer.objects.filter(tenant=tenant_a)
        
        assert tenant_a_issuers.count() == 1
        assert issuer_a in tenant_a_issuers
        assert issuer_b not in tenant_a_issuers
    
    def test_tenant_b_cannot_see_tenant_a_shareholders(
        self, tenant_a, tenant_b, shareholder_a, shareholder_b
    ):
        """Tenant B's shareholders don't include Tenant A's shareholders."""
        tenant_b_shareholders = Shareholder.objects.filter(tenant=tenant_b)
        
        assert tenant_b_shareholders.count() == 1
        assert shareholder_b in tenant_b_shareholders
        assert shareholder_a not in tenant_b_shareholders
    
    def test_membership_correctly_links_user_to_tenant(self, admin_user_a, tenant_a, tenant_b):
        """User membership correctly identifies tenant association."""
        membership = TenantMembership.objects.filter(user=admin_user_a).first()
        
        assert membership is not None
        assert membership.tenant == tenant_a
        assert membership.tenant != tenant_b
    
    def test_user_role_correctly_reflected(self, admin_user_a, shareholder_a, tenant_a):
        """User roles are correctly assigned and queryable."""
        admin_membership = TenantMembership.objects.get(user=admin_user_a, tenant=tenant_a)
        shareholder_membership = TenantMembership.objects.get(user=shareholder_a.user, tenant=tenant_a)
        
        assert admin_membership.role == 'TENANT_ADMIN'
        assert shareholder_membership.role == 'SHAREHOLDER'


@pytest.mark.django_db
class TestTenantQuerySetMixin:
    """Tests for TenantQuerySetMixin behavior."""
    
    def test_mixin_filters_by_tenant(self, tenant_a, tenant_b, issuer_a, issuer_b, admin_user_a):
        """TenantQuerySetMixin filters queryset to user's tenant."""
        from rest_framework.viewsets import ModelViewSet
        from rest_framework.serializers import ModelSerializer
        
        class IssuerSerializer(ModelSerializer):
            class Meta:
                model = Issuer
                fields = ['id', 'company_name']
        
        class TestViewSet(TenantQuerySetMixin, ModelViewSet):
            queryset = Issuer.objects.all()
            serializer_class = IssuerSerializer
        
        mock_user = Mock()
        mock_user.is_authenticated = True
        
        viewset = TestViewSet()
        viewset.request = Mock()
        viewset.request.user = mock_user
        viewset.request.tenant = tenant_a
        viewset.request.tenant_role = 'TENANT_ADMIN'
        viewset.request.query_params = {}
        
        queryset = viewset.get_queryset()
        
        assert queryset.count() == 1
        assert issuer_a in queryset
        assert issuer_b not in queryset
    
    def test_mixin_returns_empty_for_unauthenticated(self, tenant_a, issuer_a):
        """TenantQuerySetMixin returns empty queryset for unauthenticated users."""
        from rest_framework.viewsets import ModelViewSet
        from rest_framework.serializers import ModelSerializer
        
        class IssuerSerializer(ModelSerializer):
            class Meta:
                model = Issuer
                fields = ['id', 'company_name']
        
        class TestViewSet(TenantQuerySetMixin, ModelViewSet):
            queryset = Issuer.objects.all()
            serializer_class = IssuerSerializer
        
        viewset = TestViewSet()
        viewset.request = Mock()
        viewset.request.user = None
        
        queryset = viewset.get_queryset()
        
        assert queryset.count() == 0
    
    def test_mixin_platform_admin_sees_all(
        self, tenant_a, tenant_b, issuer_a, issuer_b, platform_admin
    ):
        """TenantQuerySetMixin allows platform admin to see all tenants."""
        from rest_framework.viewsets import ModelViewSet
        from rest_framework.serializers import ModelSerializer
        
        class IssuerSerializer(ModelSerializer):
            class Meta:
                model = Issuer
                fields = ['id', 'company_name']
        
        class TestViewSet(TenantQuerySetMixin, ModelViewSet):
            queryset = Issuer.objects.all()
            serializer_class = IssuerSerializer
        
        mock_user = Mock()
        mock_user.is_authenticated = True
        
        viewset = TestViewSet()
        viewset.request = Mock()
        viewset.request.user = mock_user
        viewset.request.tenant_role = 'PLATFORM_ADMIN'
        viewset.request.query_params = {}
        
        queryset = viewset.get_queryset()
        
        assert queryset.count() == 2
        assert issuer_a in queryset
        assert issuer_b in queryset
    
    def test_mixin_platform_admin_filter_by_tenant_id(
        self, tenant_a, tenant_b, issuer_a, issuer_b, platform_admin
    ):
        """TenantQuerySetMixin allows platform admin to filter by tenant_id."""
        from rest_framework.viewsets import ModelViewSet
        from rest_framework.serializers import ModelSerializer
        
        class IssuerSerializer(ModelSerializer):
            class Meta:
                model = Issuer
                fields = ['id', 'company_name']
        
        class TestViewSet(TenantQuerySetMixin, ModelViewSet):
            queryset = Issuer.objects.all()
            serializer_class = IssuerSerializer
        
        mock_user = Mock()
        mock_user.is_authenticated = True
        
        viewset = TestViewSet()
        viewset.request = Mock()
        viewset.request.user = mock_user
        viewset.request.tenant_role = 'PLATFORM_ADMIN'
        viewset.request.query_params = {'tenant_id': str(tenant_b.id)}
        
        queryset = viewset.get_queryset()
        
        assert queryset.count() == 1
        assert issuer_b in queryset
        assert issuer_a not in queryset
