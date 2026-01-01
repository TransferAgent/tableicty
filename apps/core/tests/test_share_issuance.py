"""
Tests for share issuance security and payment flow.
Covers the payment-first share issuance flow with Stripe integration.
"""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.core.models import (
    Tenant, TenantMembership, SubscriptionPlan, 
    Issuer, SecurityClass, Shareholder, Holding, ShareIssuanceRequest
)

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
        price_monthly=199.00,
        price_yearly=1990.00,
        max_shareholders=100,
        max_users=3,
        max_transfers_per_month=10,
        features=['basic_captable']
    )


@pytest.fixture
def tenant(db):
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
def issuer(db, tenant):
    from datetime import date
    return Issuer.objects.create(
        tenant=tenant,
        company_name='Test Corp',
        ticker_symbol='TEST',
        incorporation_state='DE',
        incorporation_country='US',
        total_authorized_shares=10000000,
        par_value=Decimal('0.0001'),
        agreement_start_date=date.today(),
        annual_fee=Decimal('1000.00')
    )


@pytest.fixture
def security_class(db, issuer):
    return SecurityClass.objects.create(
        issuer=issuer,
        class_designation='Common Stock',
        security_type='COMMON',
        par_value=Decimal('0.0001'),
        shares_authorized=5000000,
        voting_rights=True
    )


@pytest.fixture
def shareholder(db, tenant):
    return Shareholder.objects.create(
        tenant=tenant,
        first_name='John',
        last_name='Doe',
        account_type='INDIVIDUAL'
    )


@pytest.fixture
def authenticated_client(api_client, tenant_admin, tenant):
    api_client.force_authenticate(user=tenant_admin)
    api_client.credentials(HTTP_X_TENANT_ID=str(tenant.id))
    return api_client


@pytest.mark.django_db
class TestShareIssuanceValidation:
    """Tests for share issuance input validation."""

    def test_reject_zero_share_quantity(self, authenticated_client, shareholder, issuer, security_class):
        """Test that zero share quantity is rejected."""
        response = authenticated_client.post('/api/v1/holdings/issue-shares/', {
            'shareholder_id': str(shareholder.id),
            'issuer_id': str(issuer.id),
            'security_class_id': str(security_class.id),
            'share_quantity': 0,
            'price_per_share': '1.00',
            'investment_type': 'FOUNDER_SHARES'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Share quantity must be greater than 0' in response.data.get('error', '')

    def test_reject_negative_share_quantity(self, authenticated_client, shareholder, issuer, security_class):
        """Test that negative share quantity is rejected."""
        response = authenticated_client.post('/api/v1/holdings/issue-shares/', {
            'shareholder_id': str(shareholder.id),
            'issuer_id': str(issuer.id),
            'security_class_id': str(security_class.id),
            'share_quantity': -100,
            'price_per_share': '1.00',
            'investment_type': 'FOUNDER_SHARES'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Share quantity must be greater than 0' in response.data.get('error', '')

    def test_reject_zero_price_for_payment_required(self, authenticated_client, shareholder, issuer, security_class, tenant):
        """Test that zero price is rejected for payment-required investment types."""
        tenant.stripe_account_id = 'acct_test123'
        tenant.save()
        
        response = authenticated_client.post('/api/v1/holdings/issue-shares/', {
            'shareholder_id': str(shareholder.id),
            'issuer_id': str(issuer.id),
            'security_class_id': str(security_class.id),
            'share_quantity': 100,
            'price_per_share': '0.00',
            'investment_type': 'RETAIL'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'price per share' in response.data.get('error', '').lower()

    def test_founder_shares_issued_immediately(self, authenticated_client, shareholder, issuer, security_class):
        """Test that founder shares are issued immediately without payment."""
        response = authenticated_client.post('/api/v1/holdings/issue-shares/', {
            'shareholder_id': str(shareholder.id),
            'issuer_id': str(issuer.id),
            'security_class_id': str(security_class.id),
            'share_quantity': 1000,
            'price_per_share': '0.001',
            'investment_type': 'FOUNDER_SHARES'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data.get('requires_payment') == False
        assert 'holding' in response.data

    def test_seed_round_issued_immediately(self, authenticated_client, shareholder, issuer, security_class):
        """Test that seed round shares are issued immediately without payment."""
        response = authenticated_client.post('/api/v1/holdings/issue-shares/', {
            'shareholder_id': str(shareholder.id),
            'issuer_id': str(issuer.id),
            'security_class_id': str(security_class.id),
            'share_quantity': 500,
            'price_per_share': '1.00',
            'investment_type': 'SEED_ROUND'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data.get('requires_payment') == False

    def test_retail_requires_stripe_configuration(self, authenticated_client, shareholder, issuer, security_class, tenant):
        """Test that retail investment fails if Stripe is not configured."""
        tenant.stripe_account_id = None
        tenant.save()
        
        response = authenticated_client.post('/api/v1/holdings/issue-shares/', {
            'shareholder_id': str(shareholder.id),
            'issuer_id': str(issuer.id),
            'security_class_id': str(security_class.id),
            'share_quantity': 100,
            'price_per_share': '5.00',
            'investment_type': 'RETAIL'
        })
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert 'Stripe' in response.data.get('error', '') or 'payment' in response.data.get('error', '').lower()


@pytest.mark.django_db
class TestWebhookPaymentValidation:
    """Tests for webhook payment verification security."""

    @pytest.fixture
    def issuance_request(self, db, tenant, shareholder, issuer, security_class):
        return ShareIssuanceRequest.objects.create(
            tenant=tenant,
            shareholder=shareholder,
            issuer=issuer,
            security_class=security_class,
            share_quantity=100,
            price_per_share=Decimal('5.00'),
            total_amount=Decimal('500.00'),
            cost_basis=Decimal('500.00'),
            investment_type='RETAIL',
            status='PENDING_PAYMENT',
            stripe_checkout_session_id='cs_test_valid123',
            holding_type='BOOK_ENTRY',
            is_restricted=False,
            send_email_notification=False
        )

    def test_reject_session_id_mismatch(self, issuance_request):
        """Test that mismatched session ID is rejected."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        session = {
            'id': 'cs_test_WRONG_SESSION',
            'metadata': {'issuance_request_id': str(issuance_request.id)},
            'amount_total': 50000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        issuance_request.refresh_from_db()
        assert issuance_request.status == 'FAILED'
        assert 'Session ID mismatch' in issuance_request.notes

    def test_reject_amount_mismatch(self, issuance_request):
        """Test that payment amount mismatch is rejected."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(issuance_request.id)},
            'amount_total': 10000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        issuance_request.refresh_from_db()
        assert issuance_request.status == 'FAILED'
        assert 'Amount mismatch' in issuance_request.notes

    def test_reject_unpaid_status(self, issuance_request):
        """Test that unpaid payment status is rejected."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(issuance_request.id)},
            'amount_total': 50000,
            'payment_status': 'unpaid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        issuance_request.refresh_from_db()
        assert issuance_request.status == 'FAILED'
        assert 'Payment not confirmed' in issuance_request.notes

    def test_successful_payment_creates_holding(self, issuance_request):
        """Test that valid payment creates holding and completes issuance."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        initial_holding_count = Holding.objects.filter(
            shareholder=issuance_request.shareholder
        ).count()
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(issuance_request.id)},
            'amount_total': 50000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        issuance_request.refresh_from_db()
        assert issuance_request.status == 'COMPLETED'
        assert issuance_request.holding is not None
        
        new_holding_count = Holding.objects.filter(
            shareholder=issuance_request.shareholder
        ).count()
        assert new_holding_count == initial_holding_count + 1

    def test_idempotency_prevents_duplicate_holdings(self, issuance_request):
        """Test that duplicate webhook calls don't create duplicate holdings."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(issuance_request.id)},
            'amount_total': 50000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        initial_holding_count = Holding.objects.filter(
            shareholder=issuance_request.shareholder
        ).count()
        
        handle_share_issuance_payment(session)
        
        final_holding_count = Holding.objects.filter(
            shareholder=issuance_request.shareholder
        ).count()
        assert final_holding_count == initial_holding_count

    def test_reject_already_completed_request(self, issuance_request):
        """Test that already completed requests are skipped."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        issuance_request.status = 'COMPLETED'
        issuance_request.save()
        
        initial_holding_count = Holding.objects.count()
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(issuance_request.id)},
            'amount_total': 50000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        assert Holding.objects.count() == initial_holding_count

    def test_missing_issuance_request_id(self):
        """Test that missing issuance request ID is handled gracefully."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        session = {
            'id': 'cs_test123',
            'metadata': {},
            'amount_total': 50000,
            'payment_status': 'paid'
        }
        
        handle_share_issuance_payment(session)

    def test_nonexistent_issuance_request(self):
        """Test that nonexistent issuance request is handled gracefully."""
        from apps.core.webhooks import handle_share_issuance_payment
        import uuid
        
        session = {
            'id': 'cs_test123',
            'metadata': {'issuance_request_id': str(uuid.uuid4())},
            'amount_total': 50000,
            'payment_status': 'paid'
        }
        
        handle_share_issuance_payment(session)
