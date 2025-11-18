import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from apps.core.models import Shareholder, Issuer, SecurityClass, Holding, Transfer


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create test user with email"""
    return User.objects.create_user(
        username='test@example.com',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def test_shareholder(db, test_user):
    """Create test shareholder linked to test_user"""
    shareholder = Shareholder.objects.create(
        user=test_user,
        email='test@example.com',
        first_name='John',
        last_name='Doe',
        account_type='INDIVIDUAL',
        address_line1='123 Main St',
        city='New York',
        state='NY',
        zip_code='10001',
        country='US'
    )
    return shareholder


@pytest.fixture
def test_issuer(db):
    """Create test issuer"""
    from datetime import date
    return Issuer.objects.create(
        company_name='Test Corp',
        ticker_symbol='TEST',
        total_authorized_shares=1000000,
        incorporation_state='DE',
        agreement_start_date=date(2024, 1, 1),
        annual_fee=5000.00,
        primary_contact_name='Jane Smith',
        primary_contact_email='jane@testcorp.com',
        primary_contact_phone='555-0100'
    )


@pytest.fixture
def test_security_class(db, test_issuer):
    """Create test security class"""
    return SecurityClass.objects.create(
        issuer=test_issuer,
        security_type='COMMON',
        class_designation='Common Stock',
        shares_authorized=1000000
    )


@pytest.fixture
def test_holding(db, test_shareholder, test_issuer, test_security_class):
    """Create test holding"""
    from datetime import date
    return Holding.objects.create(
        shareholder=test_shareholder,
        issuer=test_issuer,
        security_class=test_security_class,
        share_quantity=1000,
        acquisition_date=date(2024, 1, 15)
    )


@pytest.fixture
def test_transfer(db, test_shareholder, test_issuer, test_security_class):
    """Create test transfer"""
    from datetime import date
    # Create a second shareholder for the transfer
    second_shareholder = Shareholder.objects.create(
        email='buyer@example.com',
        first_name='Bob',
        last_name='Smith',
        account_type='INDIVIDUAL',
        address_line1='456 Oak Ave',
        city='Los Angeles',
        state='CA',
        zip_code='90001',
        country='US'
    )
    return Transfer.objects.create(
        issuer=test_issuer,
        security_class=test_security_class,
        from_shareholder=test_shareholder,
        to_shareholder=second_shareholder,
        share_quantity=100,
        transfer_date=date(2025, 11, 18),
        transfer_type='SALE',
        status='EXECUTED'
    )
