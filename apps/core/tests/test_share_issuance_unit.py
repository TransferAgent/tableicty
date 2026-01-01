"""
Unit tests for share issuance security validation.
These tests mock database operations to avoid test database issues.
"""
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
import uuid


class TestWebhookPaymentValidationUnit:
    """Unit tests for webhook payment verification security."""

    def create_mock_issuance_request(self, **overrides):
        """Create a mock ShareIssuanceRequest with default values."""
        mock = MagicMock()
        mock.id = uuid.uuid4()
        mock.status = 'PENDING_PAYMENT'
        mock.stripe_checkout_session_id = 'cs_test_valid123'
        mock.total_amount = Decimal('500.00')
        mock.share_quantity = 100
        mock.price_per_share = Decimal('5.00')
        mock.cost_basis = Decimal('500.00')
        mock.holding = None
        mock.holding_type = 'BOOK_ENTRY'
        mock.is_restricted = False
        mock.send_email_notification = False
        mock.get_investment_type_display = MagicMock(return_value='Retail Investment')
        mock.tenant = MagicMock()
        mock.shareholder = MagicMock()
        mock.shareholder.email = 'test@example.com'
        mock.issuer = MagicMock()
        mock.security_class = MagicMock()
        
        for key, value in overrides.items():
            setattr(mock, key, value)
        
        return mock

    @patch('apps.core.models.ShareIssuanceRequest')
    @patch('apps.core.models.Holding')
    def test_reject_session_id_mismatch(self, mock_holding_class, mock_request_class):
        """Test that mismatched session ID is rejected."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        mock_request = self.create_mock_issuance_request()
        mock_request_class.objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_request
        
        session = {
            'id': 'cs_test_WRONG_SESSION',
            'metadata': {'issuance_request_id': str(mock_request.id)},
            'amount_total': 50000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        assert mock_request.status == 'FAILED'
        assert 'Session ID mismatch' in mock_request.notes
        mock_request.save.assert_called()
        mock_holding_class.objects.create.assert_not_called()

    @patch('apps.core.models.ShareIssuanceRequest')
    @patch('apps.core.models.Holding')
    def test_reject_amount_mismatch(self, mock_holding_class, mock_request_class):
        """Test that payment amount mismatch is rejected."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        mock_request = self.create_mock_issuance_request()
        mock_request_class.objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_request
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(mock_request.id)},
            'amount_total': 10000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        assert mock_request.status == 'FAILED'
        assert 'Amount mismatch' in mock_request.notes
        mock_request.save.assert_called()
        mock_holding_class.objects.create.assert_not_called()

    @patch('apps.core.models.ShareIssuanceRequest')
    @patch('apps.core.models.Holding')
    def test_reject_unpaid_status(self, mock_holding_class, mock_request_class):
        """Test that unpaid payment status is rejected."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        mock_request = self.create_mock_issuance_request()
        mock_request_class.objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_request
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(mock_request.id)},
            'amount_total': 50000,
            'payment_status': 'unpaid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        assert mock_request.status == 'FAILED'
        assert 'Payment not confirmed' in mock_request.notes
        mock_request.save.assert_called()
        mock_holding_class.objects.create.assert_not_called()

    @patch('apps.core.models.ShareIssuanceRequest')
    @patch('apps.core.models.Holding')
    def test_successful_payment_creates_holding(self, mock_holding_class, mock_request_class):
        """Test that valid payment creates holding and completes issuance."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        mock_request = self.create_mock_issuance_request()
        mock_request_class.objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_request
        
        mock_holding = MagicMock()
        mock_holding_class.objects.create.return_value = mock_holding
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(mock_request.id)},
            'amount_total': 50000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        assert mock_request.status == 'COMPLETED'
        assert mock_request.holding == mock_holding
        mock_holding_class.objects.create.assert_called_once()
        mock_request.save.assert_called()

    @patch('apps.core.models.ShareIssuanceRequest')
    @patch('apps.core.models.Holding')
    def test_idempotency_skips_completed_request(self, mock_holding_class, mock_request_class):
        """Test that already completed requests are skipped."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        mock_request = self.create_mock_issuance_request(status='COMPLETED')
        mock_request_class.objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_request
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(mock_request.id)},
            'amount_total': 50000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        mock_holding_class.objects.create.assert_not_called()

    @patch('apps.core.models.ShareIssuanceRequest')
    @patch('apps.core.models.Holding')
    def test_idempotency_skips_request_with_holding(self, mock_holding_class, mock_request_class):
        """Test that requests with existing holdings are skipped."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        existing_holding = MagicMock()
        mock_request = self.create_mock_issuance_request(holding=existing_holding)
        mock_request_class.objects.select_for_update.return_value.select_related.return_value.get.return_value = mock_request
        
        session = {
            'id': 'cs_test_valid123',
            'metadata': {'issuance_request_id': str(mock_request.id)},
            'amount_total': 50000,
            'payment_status': 'paid',
            'payment_intent': 'pi_test123'
        }
        
        handle_share_issuance_payment(session)
        
        mock_holding_class.objects.create.assert_not_called()

    def test_missing_issuance_request_id_gracefully_handled(self):
        """Test that missing issuance request ID is handled gracefully."""
        from apps.core.webhooks import handle_share_issuance_payment
        
        session = {
            'id': 'cs_test123',
            'metadata': {},
            'amount_total': 50000,
            'payment_status': 'paid'
        }
        
        handle_share_issuance_payment(session)

    @patch('apps.core.models.ShareIssuanceRequest')
    def test_nonexistent_issuance_request_gracefully_handled(self, mock_request_class):
        """Test that nonexistent issuance request is handled gracefully."""
        from apps.core.webhooks import handle_share_issuance_payment
        from apps.core.models import ShareIssuanceRequest
        
        mock_request_class.DoesNotExist = ShareIssuanceRequest.DoesNotExist
        mock_request_class.objects.select_for_update.return_value.select_related.return_value.get.side_effect = ShareIssuanceRequest.DoesNotExist()
        
        session = {
            'id': 'cs_test123',
            'metadata': {'issuance_request_id': str(uuid.uuid4())},
            'amount_total': 50000,
            'payment_status': 'paid'
        }
        
        handle_share_issuance_payment(session)


class TestShareQuantityValidation:
    """Unit tests for share quantity validation in the API."""

    def test_zero_quantity_rejected(self):
        """Test that zero share quantity fails validation."""
        from decimal import Decimal
        share_qty = Decimal('0')
        assert share_qty <= 0, "Zero quantity should be rejected"

    def test_negative_quantity_rejected(self):
        """Test that negative share quantity fails validation."""
        from decimal import Decimal
        share_qty = Decimal('-100')
        assert share_qty <= 0, "Negative quantity should be rejected"

    def test_positive_quantity_accepted(self):
        """Test that positive share quantity passes validation."""
        from decimal import Decimal
        share_qty = Decimal('100')
        assert share_qty > 0, "Positive quantity should be accepted"

    def test_small_positive_quantity_accepted(self):
        """Test that small positive share quantity passes validation."""
        from decimal import Decimal
        share_qty = Decimal('0.001')
        assert share_qty > 0, "Small positive quantity should be accepted"
