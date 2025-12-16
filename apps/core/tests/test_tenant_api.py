"""
Tests for tenant management API endpoints.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.core.models import Tenant, TenantMembership, SubscriptionPlan, TenantInvitation

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def subscription_plan(db):
    return SubscriptionPlan.objects.create(
        name='Starter',
        slug='starter',
        tier='STARTER',
        price_monthly=49.00,
        price_yearly=490.00,
        max_shareholders=100,
        max_users=3,
        max_transfers_per_month=10,
        features=['basic_captable']
    )


@pytest.fixture
def tenant(db, subscription_plan):
    return Tenant.objects.create(
        name='Test Company',
        slug='test-company',
        primary_email='admin@test.com',
        status='ACTIVE'
    )


@pytest.fixture
def tenant_admin(db, tenant):
    user = User.objects.create_user(
        username='admin@test.com',
        email='admin@test.com',
        password='testpass123'
    )
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role='TENANT_ADMIN'
    )
    return user


@pytest.fixture
def tenant_staff(db, tenant):
    user = User.objects.create_user(
        username='staff@test.com',
        email='staff@test.com',
        password='testpass123'
    )
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role='TENANT_STAFF'
    )
    return user


@pytest.fixture
def shareholder_user(db, tenant):
    user = User.objects.create_user(
        username='shareholder@test.com',
        email='shareholder@test.com',
        password='testpass123'
    )
    TenantMembership.objects.create(
        tenant=tenant,
        user=user,
        role='SHAREHOLDER'
    )
    return user


@pytest.mark.django_db
class TestTenantRegistration:
    """Tests for tenant self-registration endpoint."""
    
    def test_register_new_tenant_success(self, api_client, subscription_plan):
        """Test successful tenant registration."""
        response = api_client.post('/api/v1/tenant/register/', {
            'company_name': 'New Company Inc',
            'company_slug': 'new-company',
            'email': 'owner@newcompany.com',
            'password': 'securepass123',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'tenant' in response.data
        assert 'access' in response.data
        assert response.data['tenant']['name'] == 'New Company Inc'
        assert response.data['tenant']['slug'] == 'new-company'
        
        tenant = Tenant.objects.get(slug='new-company')
        assert tenant is not None
        
        membership = TenantMembership.objects.get(tenant=tenant)
        assert membership.role == 'TENANT_ADMIN'
        assert membership.user.email == 'owner@newcompany.com'
    
    def test_register_duplicate_slug_fails(self, api_client, tenant, subscription_plan):
        """Test registration with existing slug fails."""
        response = api_client.post('/api/v1/tenant/register/', {
            'company_name': 'Another Company',
            'company_slug': 'test-company',
            'email': 'new@test.com',
            'password': 'securepass123'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_duplicate_email_fails(self, api_client, tenant_admin, subscription_plan):
        """Test registration with existing email fails."""
        response = api_client.post('/api/v1/tenant/register/', {
            'company_name': 'New Company',
            'company_slug': 'new-company',
            'email': 'admin@test.com',
            'password': 'securepass123'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTenantSettings:
    """Tests for tenant settings endpoint."""
    
    def test_get_tenant_settings_as_admin(self, api_client, tenant, tenant_admin):
        """Test tenant admin can view settings."""
        api_client.force_authenticate(user=tenant_admin)
        response = api_client.get('/api/v1/tenant/settings/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Company'
    
    def test_update_tenant_settings_as_admin(self, api_client, tenant, tenant_admin):
        """Test tenant admin can update settings."""
        api_client.force_authenticate(user=tenant_admin)
        response = api_client.patch('/api/v1/tenant/settings/', {
            'name': 'Updated Company Name'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Company Name'
    
    def test_staff_cannot_update_tenant_settings(self, api_client, tenant, tenant_staff):
        """Test tenant staff cannot update settings."""
        api_client.force_authenticate(user=tenant_staff)
        response = api_client.patch('/api/v1/tenant/settings/', {
            'name': 'Hacked Name'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_shareholder_cannot_access_tenant_settings(self, api_client, tenant, shareholder_user):
        """Test shareholders cannot access tenant settings."""
        api_client.force_authenticate(user=shareholder_user)
        response = api_client.get('/api/v1/tenant/settings/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTenantInvitations:
    """Tests for tenant invitation endpoints."""
    
    def test_create_invitation_as_admin(self, api_client, tenant, tenant_admin):
        """Test tenant admin can create invitations."""
        api_client.force_authenticate(user=tenant_admin)
        response = api_client.post('/api/v1/tenant/invitations/', {
            'email': 'newuser@test.com',
            'role': 'TENANT_STAFF'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert TenantInvitation.objects.filter(email='newuser@test.com').exists()
    
    def test_create_invitation_as_staff(self, api_client, tenant, tenant_staff):
        """Test tenant staff can create invitations for shareholders."""
        api_client.force_authenticate(user=tenant_staff)
        response = api_client.post('/api/v1/tenant/invitations/', {
            'email': 'newshareholder@test.com',
            'role': 'SHAREHOLDER'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_staff_cannot_invite_tenant_admin(self, api_client, tenant, tenant_staff):
        """Test staff cannot invite tenant admins."""
        api_client.force_authenticate(user=tenant_staff)
        response = api_client.post('/api/v1/tenant/invitations/', {
            'email': 'newadmin@test.com',
            'role': 'TENANT_ADMIN'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_validate_invitation_token(self, api_client, tenant, tenant_admin):
        """Test validating an invitation token."""
        api_client.force_authenticate(user=tenant_admin)
        response = api_client.post('/api/v1/tenant/invitations/', {
            'email': 'invited@test.com',
            'role': 'SHAREHOLDER'
        })
        
        invitation = TenantInvitation.objects.get(email='invited@test.com')
        
        api_client.logout()
        response = api_client.get(f'/api/v1/tenant/invitations/validate/{invitation.token}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['valid'] is True
        assert response.data['email'] == 'invited@test.com'
    
    def test_accept_invitation_new_user(self, api_client, tenant, tenant_admin):
        """Test accepting an invitation as a new user."""
        api_client.force_authenticate(user=tenant_admin)
        api_client.post('/api/v1/tenant/invitations/', {
            'email': 'newmember@test.com',
            'role': 'TENANT_STAFF'
        })
        
        invitation = TenantInvitation.objects.get(email='newmember@test.com')
        
        api_client.logout()
        response = api_client.post(f'/api/v1/tenant/invitations/accept/{invitation.token}/', {
            'password': 'newuserpass123',
            'first_name': 'New',
            'last_name': 'Member'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data
        
        user = User.objects.get(email='newmember@test.com')
        membership = TenantMembership.objects.get(user=user, tenant=tenant)
        assert membership.role == 'TENANT_STAFF'
        
        invitation.refresh_from_db()
        assert invitation.status == 'ACCEPTED'


@pytest.mark.django_db
class TestTenantMembers:
    """Tests for tenant membership management."""
    
    def test_list_members_as_admin(self, api_client, tenant, tenant_admin, tenant_staff):
        """Test admin can list all members."""
        api_client.force_authenticate(user=tenant_admin)
        response = api_client.get('/api/v1/tenant/members/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
    
    def test_list_members_as_staff(self, api_client, tenant, tenant_admin, tenant_staff):
        """Test staff can list members."""
        api_client.force_authenticate(user=tenant_staff)
        response = api_client.get('/api/v1/tenant/members/')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_shareholder_cannot_list_members(self, api_client, tenant, shareholder_user):
        """Test shareholders cannot list tenant members."""
        api_client.force_authenticate(user=shareholder_user)
        response = api_client.get('/api/v1/tenant/members/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_admin_cannot_remove_self(self, api_client, tenant, tenant_admin):
        """Test admin cannot remove themselves."""
        api_client.force_authenticate(user=tenant_admin)
        membership = TenantMembership.objects.get(user=tenant_admin, tenant=tenant)
        
        response = api_client.delete(f'/api/v1/tenant/members/{membership.id}/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCurrentTenant:
    """Tests for current tenant endpoint."""
    
    def test_get_current_tenant_authenticated(self, api_client, tenant, tenant_admin):
        """Test getting current tenant info."""
        api_client.force_authenticate(user=tenant_admin)
        response = api_client.get('/api/v1/tenant/current/')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_current_tenant_unauthenticated(self, api_client):
        """Test unauthenticated access is denied."""
        response = api_client.get('/api/v1/tenant/current/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
