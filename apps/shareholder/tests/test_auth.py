import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from apps.core.models import Shareholder


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.fixture
def registered_user_and_shareholder(db):
    """Create a user and separate shareholder record (no FK relationship)"""
    user = User.objects.create_user(
        username='testuser@example.com',
        email='testuser@example.com',
        password='TestPass123!'
    )
    shareholder = Shareholder.objects.create(
        email='testuser@example.com',
        first_name='Test',
        last_name='User',
        account_type='INDIVIDUAL',
        address_line1='123 Test St',
        city='Test City',
        state='TS',
        zip_code='12345',
        country='US'
    )
    return {'user': user, 'shareholder': shareholder}


@pytest.mark.django_db
class TestShareholderAuthentication:
    """Test shareholder authentication endpoints"""
    
    def test_login_success(self, api_client, registered_user_and_shareholder):
        """Test successful login with valid credentials"""
        response = api_client.post('/api/v1/shareholder/auth/login/', {
            'username': 'testuser@example.com',
            'password': 'TestPass123!'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['access'] is not None
        assert response.data['refresh'] is not None
    
    def test_login_wrong_password(self, api_client, registered_user_and_shareholder):
        """Test login fails with wrong password"""
        response = api_client.post('/api/v1/shareholder/auth/login/', {
            'username': 'testuser@example.com',
            'password': 'WrongPassword123!'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_user_not_found(self, api_client):
        """Test login fails when user doesn't exist"""
        response = api_client.post('/api/v1/shareholder/auth/login/', {
            'username': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_missing_credentials(self, api_client):
        """Test login fails with missing credentials"""
        response = api_client.post('/api/v1/shareholder/auth/login/', {
            'username': 'testuser@example.com'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.skip(reason="Invite token validation infrastructure not yet implemented")
    def test_register_success(self, api_client, db):
        """Test successful user registration"""
        Shareholder.objects.create(
            email='newuser@example.com',
            first_name='New',
            last_name='User',
            account_type='INDIVIDUAL',
            address_line1='456 New St',
            city='New City',
            state='NC',
            zip_code='67890',
            country='US'
        )
        
        response = api_client.post('/api/v1/shareholder/auth/register/', {
            'email': 'newuser@example.com',
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!',
            'invite_token': 'valid-token-123'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data
        assert response.data['message'] == 'Registration successful'
        
        assert User.objects.filter(email='newuser@example.com').exists()
        shareholder = Shareholder.objects.get(email='newuser@example.com')
        assert shareholder.user is not None
    
    def test_register_password_mismatch(self, api_client, db):
        """Test registration fails when passwords don't match"""
        Shareholder.objects.create(
            email='newuser@example.com',
            first_name='New',
            last_name='User',
            account_type='INDIVIDUAL',
            address_line1='456 New St',
            city='New City',
            state='NC',
            zip_code='67890'
        )
        
        response = api_client.post('/api/v1/shareholder/auth/register/', {
            'email': 'newuser@example.com',
            'password': 'NewPass123!',
            'password_confirm': 'DifferentPass123!',
            'invite_token': 'valid-token-123'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_duplicate_email(self, api_client, registered_user_and_shareholder):
        """Test registration fails with duplicate email"""
        response = api_client.post('/api/v1/shareholder/auth/register/', {
            'email': 'testuser@example.com',
            'password': 'NewPass123!',
            'password_confirm': 'NewPass123!',
            'invite_token': 'valid-token-123'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_logout_success(self, api_client, registered_user_and_shareholder):
        """Test successful logout with valid refresh token"""
        login_response = api_client.post('/api/v1/shareholder/auth/login/', {
            'username': 'testuser@example.com',
            'password': 'TestPass123!'
        })
        refresh_token = login_response.data['refresh']
        access_token = login_response.data['access']
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_response = api_client.post('/api/v1/shareholder/auth/logout/', {
            'refresh': refresh_token
        })
        
        assert logout_response.status_code == status.HTTP_200_OK
        assert logout_response.data['message'] == 'Logout successful'
    
    def test_logout_without_token(self, api_client, registered_user_and_shareholder):
        """Test logout fails without refresh token"""
        login_response = api_client.post('/api/v1/shareholder/auth/login/', {
            'username': 'testuser@example.com',
            'password': 'TestPass123!'
        })
        access_token = login_response.data['access']
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_response = api_client.post('/api/v1/shareholder/auth/logout/', {})
        
        assert logout_response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in logout_response.data
    
    def test_logout_unauthenticated(self, api_client):
        """Test logout fails when not authenticated"""
        response = api_client.post('/api/v1/shareholder/auth/logout/', {
            'refresh': 'some-token'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_refresh_success(self, api_client, registered_user_and_shareholder):
        """Test token refresh with valid refresh token"""
        login_response = api_client.post('/api/v1/shareholder/auth/login/', {
            'username': 'testuser@example.com',
            'password': 'TestPass123!'
        })
        refresh_token = login_response.data['refresh']
        
        refresh_response = api_client.post('/api/v1/shareholder/auth/refresh/', {
            'refresh': refresh_token
        })
        
        assert refresh_response.status_code == status.HTTP_200_OK
        assert 'access' in refresh_response.data
        assert refresh_response.data['access'] is not None
    
    def test_token_refresh_invalid_token(self, api_client):
        """Test token refresh fails with invalid token"""
        response = api_client.post('/api/v1/shareholder/auth/refresh/', {
            'refresh': 'invalid-token-string'
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_current_user_authenticated(self, api_client, registered_user_and_shareholder):
        """Test current user endpoint returns user data when authenticated"""
        login_response = api_client.post('/api/v1/shareholder/auth/login/', {
            'username': 'testuser@example.com',
            'password': 'TestPass123!'
        })
        access_token = login_response.data['access']
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.get('/api/v1/shareholder/auth/me/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'testuser@example.com'
    
    def test_current_user_unauthenticated(self, api_client):
        """Test current user endpoint fails without authentication"""
        response = api_client.get('/api/v1/shareholder/auth/me/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
