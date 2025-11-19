import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from apps.core.models import Shareholder, Holding, Transfer, Issuer, SecurityClass
from datetime import date
from decimal import Decimal


@pytest.mark.django_db
class TestShareholderDataIsolation:
    """Test that shareholders can only access their own data"""
    
    def setup_method(self):
        """Create two shareholders for testing isolation"""
        # Shareholder 1 (Alice)
        self.user1 = User.objects.create_user(
            username='alice@example.com',
            email='alice@example.com',
            password='testpass123'
        )
        self.shareholder1 = Shareholder.objects.create(
            user=self.user1,
            email='alice@example.com',
            first_name='Alice',
            last_name='Johnson',
            account_type='INDIVIDUAL',
            address_line1='123 Main St',
            city='New York',
            state='NY',
            zip_code='10001',
            country='US'
        )
        
        # Shareholder 2 (Bob)
        self.user2 = User.objects.create_user(
            username='bob@example.com',
            email='bob@example.com',
            password='testpass123'
        )
        self.shareholder2 = Shareholder.objects.create(
            user=self.user2,
            email='bob@example.com',
            first_name='Bob',
            last_name='Smith',
            account_type='INDIVIDUAL',
            address_line1='456 Oak Ave',
            city='Boston',
            state='MA',
            zip_code='02101',
            country='US'
        )
        
        # Create test issuer and security class
        self.issuer = Issuer.objects.create(
            company_name='Test Corp',
            ticker_symbol='TEST',
            total_authorized_shares=Decimal('1000000'),
            par_value=Decimal('0.0001'),
            incorporation_state='DE',
            incorporation_country='US',
            agreement_start_date=date.today(),
            annual_fee=Decimal('5000.00')
        )
        self.security_class = SecurityClass.objects.create(
            issuer=self.issuer,
            security_type='COMMON',
            class_designation='Common Stock',
            shares_authorized=Decimal('1000000')
        )
        
        # Create holdings for each shareholder
        self.alice_holding = Holding.objects.create(
            shareholder=self.shareholder1,
            issuer=self.issuer,
            security_class=self.security_class,
            share_quantity=Decimal('1000'),
            acquisition_date=date.today(),
            holding_type='DRS'
        )
        
        self.bob_holding = Holding.objects.create(
            shareholder=self.shareholder2,
            issuer=self.issuer,
            security_class=self.security_class,
            share_quantity=Decimal('2000'),
            acquisition_date=date.today(),
            holding_type='DRS'
        )
        
        # Create a company/broker shareholder to act as seller
        self.company_shareholder = Shareholder.objects.create(
            email='company@testcorp.com',
            entity_name='Test Corp Treasury',
            account_type='ENTITY',
            address_line1='789 Corporate Blvd',
            city='Wilmington',
            state='DE',
            zip_code='19801',
            country='US'
        )
        
        # Create transfers for each shareholder
        self.alice_transfer = Transfer.objects.create(
            issuer=self.issuer,
            security_class=self.security_class,
            from_shareholder=self.company_shareholder,
            to_shareholder=self.shareholder1,
            share_quantity=Decimal('500'),
            transfer_type='PURCHASE',
            status='EXECUTED',
            transfer_date=date.today()
        )
        
        self.bob_transfer = Transfer.objects.create(
            issuer=self.issuer,
            security_class=self.security_class,
            from_shareholder=self.company_shareholder,
            to_shareholder=self.shareholder2,
            share_quantity=Decimal('800'),
            transfer_type='PURCHASE',
            status='EXECUTED',
            transfer_date=date.today()
        )
        
        self.client = APIClient()
    
    def test_alice_can_access_own_profile(self):
        """Alice can view her own profile"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/v1/shareholder/profile/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'alice@example.com'
        assert response.data['first_name'] == 'Alice'
    
    def test_alice_cannot_access_bobs_profile(self):
        """Alice cannot view Bob's profile - no endpoint exists for other shareholders"""
        self.client.force_authenticate(user=self.user1)
        
        # The shareholder portal only has /api/v1/shareholder/profile/ (own profile)
        # There's no endpoint to access other shareholders by ID
        # This test verifies the profile endpoint only returns Alice's data
        response = self.client.get('/api/v1/shareholder/profile/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'alice@example.com'
        assert response.data['email'] != 'bob@example.com'
    
    def test_alice_sees_only_own_holdings(self):
        """Alice sees only her holdings, not Bob's"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/v1/shareholder/holdings/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['holdings']) == 1
        assert response.data['holdings'][0]['share_quantity'] == '1000'
    
    def test_bob_sees_only_own_holdings(self):
        """Bob sees only his holdings, not Alice's"""
        self.client.force_authenticate(user=self.user2)
        
        response = self.client.get('/api/v1/shareholder/holdings/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['holdings']) == 1
        assert response.data['holdings'][0]['share_quantity'] == '2000'
    
    def test_alice_sees_only_own_transactions(self):
        """Alice sees only her transactions, not Bob's"""
        self.client.force_authenticate(user=self.user1)
        
        response = self.client.get('/api/v1/shareholder/transactions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['transfers']) == 1
        assert float(response.data['transfers'][0]['share_quantity']) == 500
    
    def test_bob_sees_only_own_transactions(self):
        """Bob sees only his transactions, not Alice's"""
        self.client.force_authenticate(user=self.user2)
        
        response = self.client.get('/api/v1/shareholder/transactions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['transfers']) == 1
        assert float(response.data['transfers'][0]['share_quantity']) == 800
    
    def test_alice_cannot_update_bobs_profile(self):
        """Alice cannot modify Bob's profile via her own profile endpoint"""
        self.client.force_authenticate(user=self.user1)
        
        # Profile endpoint only updates current user's shareholder
        response = self.client.patch(
            '/api/v1/shareholder/profile/',
            {'first_name': 'HACKED'}
        )
        
        # This will succeed for Alice's profile (expected behavior)
        assert response.status_code == status.HTTP_200_OK
        
        # Verify Bob's profile unchanged
        self.shareholder2.refresh_from_db()
        assert self.shareholder2.first_name == 'Bob'
        
        # Verify Alice's was updated
        self.shareholder1.refresh_from_db()
        assert self.shareholder1.first_name == 'HACKED'
    
    def test_unauthenticated_cannot_access_data(self):
        """Unauthenticated users get 401 errors"""
        # Don't authenticate
        
        response_profile = self.client.get('/api/v1/shareholder/profile/')
        response_holdings = self.client.get('/api/v1/shareholder/holdings/')
        response_transactions = self.client.get('/api/v1/shareholder/transactions/')
        
        assert response_profile.status_code == status.HTTP_401_UNAUTHORIZED
        assert response_holdings.status_code == status.HTTP_401_UNAUTHORIZED
        assert response_transactions.status_code == status.HTTP_401_UNAUTHORIZED
