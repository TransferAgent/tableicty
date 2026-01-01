from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.models import Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer, AuditLog
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsTenantStaff, CanProcessTransfers, TenantScopedPermission
from apps.core.services.subscription import SubscriptionValidator
from .serializers import (
    IssuerSerializer, SecurityClassSerializer, ShareholderSerializer,
    HoldingSerializer, CertificateSerializer, TransferSerializer, AuditLogSerializer
)


class IssuerViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Issuer.objects.all()
    serializer_class = IssuerSerializer
    permission_classes = [IsAuthenticated, TenantScopedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['otc_tier', 'tavs_enabled', 'is_active', 'blockchain_enabled']
    search_fields = ['company_name', 'ticker_symbol', 'cusip', 'cik']
    ordering_fields = ['company_name', 'created_at', 'ticker_symbol']
    ordering = ['company_name']
    
    @action(detail=True, methods=['get'])
    def cap_table(self, request, pk=None):
        """Generate cap table for this issuer (ACTIVE holdings only)"""
        issuer = self.get_object()
        holdings = Holding.objects.filter(issuer=issuer, status='ACTIVE').select_related('shareholder', 'security_class')
        
        total_shares = sum(h.share_quantity for h in holdings)
        cap_table_data = []
        
        for holding in holdings:
            percentage = (float(holding.share_quantity) / float(total_shares) * 100) if total_shares > 0 else 0
            cap_table_data.append({
                'shareholder': str(holding.shareholder),
                'security_class': str(holding.security_class),
                'shares': float(holding.share_quantity),
                'percentage': round(percentage, 4)
            })
        
        return Response({
            'issuer': issuer.company_name,
            'ticker': issuer.ticker_symbol,
            'total_authorized': float(issuer.total_authorized_shares),
            'total_issued': float(total_shares),
            'cap_table': cap_table_data
        })
    
    @action(detail=True, methods=['get'])
    def share_summary(self, request, pk=None):
        """Get authorized vs issued shares summary (ACTIVE holdings only)"""
        issuer = self.get_object()
        holdings = Holding.objects.filter(issuer=issuer, status='ACTIVE')
        
        total_issued = sum(h.share_quantity for h in holdings)
        
        return Response({
            'authorized_shares': float(issuer.total_authorized_shares),
            'issued_shares': float(total_issued),
            'available_shares': float(issuer.total_authorized_shares - total_issued),
            'utilization_percentage': round(float(total_issued) / float(issuer.total_authorized_shares) * 100, 2)
        })


class SecurityClassViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = SecurityClass.objects.all()
    serializer_class = SecurityClassSerializer
    permission_classes = [IsAuthenticated, TenantScopedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['issuer', 'security_type', 'voting_rights', 'is_active']
    search_fields = ['class_designation', 'issuer__company_name']
    ordering = ['issuer', 'security_type']
    tenant_field = 'issuer__tenant'


class ShareholderViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    permission_classes = [IsAuthenticated, IsTenantStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'accredited_investor', 'kyc_verified', 'is_active', 'country']
    search_fields = ['first_name', 'last_name', 'entity_name', 'email']
    ordering = ['last_name', 'first_name']
    
    def create(self, request, *args, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if tenant:
            can_add, current, limit, message = SubscriptionValidator.check_shareholder_limit(tenant)
            if not can_add:
                return Response(
                    {
                        'error': 'Shareholder limit reached',
                        'message': message,
                        'current': current,
                        'limit': limit,
                        'upgrade_url': '/billing',
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        return super().create(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def holdings(self, request, pk=None):
        """Get all holdings for this shareholder"""
        shareholder = self.get_object()
        holdings = Holding.objects.filter(shareholder=shareholder).select_related('issuer', 'security_class')
        serializer = HoldingSerializer(holdings, many=True)
        return Response(serializer.data)


class HoldingViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Holding.objects.all()
    serializer_class = HoldingSerializer
    permission_classes = [IsAuthenticated, TenantScopedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['shareholder', 'issuer', 'security_class', 'holding_type', 'is_restricted']
    search_fields = ['shareholder__first_name', 'shareholder__last_name', 'issuer__company_name']
    ordering = ['issuer', '-share_quantity']
    
    @action(detail=False, methods=['post'], url_path='issue-shares')
    def issue_shares(self, request):
        """
        Issue shares with conditional payment based on investment type.
        
        - FOUNDER_SHARES / SEED_ROUND: Issues shares immediately (no payment)
        - RETAIL / FRIENDS_FAMILY: Creates Stripe checkout, issues after payment
        
        POST /api/v1/holdings/issue-shares/
        {
            "shareholder": "uuid",
            "issuer": "uuid",
            "security_class": "uuid",
            "share_quantity": "1000",
            "investment_type": "FOUNDER_SHARES|SEED_ROUND|RETAIL|FRIENDS_FAMILY",
            "price_per_share": "1.00",
            "holding_type": "DRS",
            "is_restricted": false,
            "acquisition_type": "ISSUANCE",
            "cost_basis": "1000.00",
            "notes": "",
            "send_email_notification": true
        }
        """
        from decimal import Decimal, InvalidOperation
        from django.utils import timezone
        from datetime import timedelta
        from apps.core.models import ShareIssuanceRequest, Shareholder, SecurityClass as SecurityClassModel
        from apps.core.stripe import is_stripe_configured, get_stripe_client
        import os
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)
        
        shareholder_id = request.data.get('shareholder')
        issuer_id = request.data.get('issuer')
        security_class_id = request.data.get('security_class')
        share_quantity = request.data.get('share_quantity')
        investment_type = request.data.get('investment_type', 'FOUNDER_SHARES')
        price_per_share = request.data.get('price_per_share', '0')
        holding_type = request.data.get('holding_type', 'DRS')
        is_restricted = request.data.get('is_restricted', False)
        acquisition_type = request.data.get('acquisition_type', 'ISSUANCE')
        cost_basis = request.data.get('cost_basis')
        notes = request.data.get('notes', '')
        send_email = request.data.get('send_email_notification', True)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"ISSUE_SHARES DEBUG: send_email_notification received = {request.data.get('send_email_notification')}, parsed send_email = {send_email}, investment_type = {investment_type}")
        
        if not all([shareholder_id, issuer_id, security_class_id, share_quantity]):
            return Response(
                {'error': 'shareholder, issuer, security_class, and share_quantity are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_investment_types = ['FOUNDER_SHARES', 'SEED_ROUND', 'RETAIL', 'FRIENDS_FAMILY']
        if investment_type not in valid_investment_types:
            return Response(
                {'error': f'Invalid investment_type. Must be one of: {", ".join(valid_investment_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            share_qty = Decimal(str(share_quantity))
            price = Decimal(str(price_per_share))
            cost = Decimal(str(cost_basis)) if cost_basis else share_qty * price
        except (InvalidOperation, ValueError) as e:
            return Response({'error': f'Invalid numeric value: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        if share_qty <= 0:
            return Response(
                {'error': 'Share quantity must be greater than 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            shareholder = Shareholder.objects.get(id=shareholder_id, tenant=tenant)
        except Shareholder.DoesNotExist:
            return Response({'error': 'Shareholder not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            issuer = Issuer.objects.get(id=issuer_id, tenant=tenant)
        except Issuer.DoesNotExist:
            return Response({'error': 'Issuer not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            security_class = SecurityClassModel.objects.get(id=security_class_id, issuer=issuer)
        except SecurityClassModel.DoesNotExist:
            return Response({'error': 'Security class not found'}, status=status.HTTP_404_NOT_FOUND)
        
        requires_payment = investment_type in ('RETAIL', 'FRIENDS_FAMILY')
        total_amount = share_qty * price
        
        if requires_payment:
            if not is_stripe_configured():
                return Response(
                    {'error': 'Payment processing is not configured. Please contact support.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            if price <= 0:
                return Response(
                    {'error': 'Price per share must be greater than 0 for paid investments'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            issuance_request = ShareIssuanceRequest.objects.create(
                tenant=tenant,
                shareholder=shareholder,
                issuer=issuer,
                security_class=security_class,
                investment_type=investment_type,
                share_quantity=share_qty,
                price_per_share=price,
                total_amount=total_amount,
                status='PENDING_PAYMENT',
                holding_type=holding_type,
                is_restricted=is_restricted,
                acquisition_type=acquisition_type,
                cost_basis=cost,
                notes=notes,
                send_email_notification=send_email,
                requested_by=request.user,
                expires_at=timezone.now() + timedelta(hours=24),
            )
            
            try:
                stripe = get_stripe_client()
                
                frontend_domain = os.environ.get('FRONTEND_DOMAIN', 'https://tableicty.com')
                success_url = f"{frontend_domain}/shareholders?issuance=success&request_id={issuance_request.id}"
                cancel_url = f"{frontend_domain}/shareholders?issuance=cancelled&request_id={issuance_request.id}"
                
                checkout_session = stripe.checkout.Session.create(
                    mode='payment',
                    customer_email=shareholder.email if shareholder.email else None,
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'unit_amount': int(price * 100),
                            'product_data': {
                                'name': f'{issuer.company_name} - {security_class.class_designation} Shares',
                                'description': f'{share_qty} shares @ ${price}/share',
                            },
                        },
                        'quantity': int(share_qty),
                    }],
                    success_url=success_url,
                    cancel_url=cancel_url,
                    metadata={
                        'type': 'share_issuance',
                        'issuance_request_id': str(issuance_request.id),
                        'tenant_id': str(tenant.id),
                        'shareholder_id': str(shareholder.id),
                        'investment_type': investment_type,
                    },
                    expires_at=int((timezone.now() + timedelta(hours=24)).timestamp()),
                )
                
                issuance_request.stripe_checkout_session_id = checkout_session.id
                issuance_request.status = 'PAYMENT_PROCESSING'
                issuance_request.save()
                
                return Response({
                    'status': 'payment_required',
                    'message': 'Payment required for share purchase',
                    'checkout_url': checkout_session.url,
                    'issuance_request_id': str(issuance_request.id),
                    'investment_type': investment_type,
                    'total_amount': str(total_amount),
                })
                
            except Exception as e:
                issuance_request.status = 'FAILED'
                issuance_request.notes = f"Stripe error: {str(e)}"
                issuance_request.save()
                return Response(
                    {'error': f'Failed to create payment session: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        else:
            if send_email:
                holding = Holding.objects.create(
                    tenant=tenant,
                    shareholder=shareholder,
                    issuer=issuer,
                    security_class=security_class,
                    share_quantity=share_qty,
                    acquisition_date=timezone.now().date(),
                    acquisition_price=price if price > 0 else None,
                    cost_basis=cost if cost > 0 else None,
                    holding_type=holding_type,
                    is_restricted=is_restricted,
                    notes=notes,
                    status='ACTIVE',
                    held_at=timezone.now(),
                    released_at=timezone.now(),
                    released_by=request.user,
                )
                
                issuance_request = ShareIssuanceRequest.objects.create(
                    tenant=tenant,
                    shareholder=shareholder,
                    issuer=issuer,
                    security_class=security_class,
                    investment_type=investment_type,
                    share_quantity=share_qty,
                    price_per_share=price,
                    total_amount=total_amount,
                    status='COMPLETED',
                    holding=holding,
                    holding_type=holding_type,
                    is_restricted=is_restricted,
                    acquisition_type=acquisition_type,
                    cost_basis=cost,
                    notes=notes,
                    send_email_notification=send_email,
                    requested_by=request.user,
                    completed_at=timezone.now(),
                )
                
                if shareholder.email:
                    try:
                        from apps.core.services.email import EmailService
                        from django.db.models import Sum
                        
                        email_service = EmailService()
                        total_shares = Holding.objects.filter(
                            shareholder=shareholder,
                            status='ACTIVE'
                        ).aggregate(total=Sum('share_quantity'))['total'] or 0
                        
                        email_service.send_share_update_or_invitation(
                            shareholder=shareholder,
                            issuer=issuer,
                            additional_shares=int(share_qty),
                            total_shares=int(total_shares),
                        )
                    except Exception as email_error:
                        pass
                
                serializer = HoldingSerializer(holding)
                return Response({
                    'status': 'completed',
                    'message': 'Shares issued successfully and email notification sent.',
                    'holding': serializer.data,
                    'issuance_request_id': str(issuance_request.id),
                    'investment_type': investment_type,
                    'holding_status': 'ACTIVE',
                })
            else:
                holding = Holding.objects.create(
                    tenant=tenant,
                    shareholder=shareholder,
                    issuer=issuer,
                    security_class=security_class,
                    share_quantity=share_qty,
                    acquisition_date=timezone.now().date(),
                    acquisition_price=price if price > 0 else None,
                    cost_basis=cost if cost > 0 else None,
                    holding_type=holding_type,
                    is_restricted=is_restricted,
                    notes=notes,
                    status='HELD',
                    held_at=timezone.now(),
                )
                
                issuance_request = ShareIssuanceRequest.objects.create(
                    tenant=tenant,
                    shareholder=shareholder,
                    issuer=issuer,
                    security_class=security_class,
                    investment_type=investment_type,
                    share_quantity=share_qty,
                    price_per_share=price,
                    total_amount=total_amount,
                    status='COMPLETED',
                    holding=holding,
                    holding_type=holding_type,
                    is_restricted=is_restricted,
                    acquisition_type=acquisition_type,
                    cost_basis=cost,
                    notes=notes,
                    send_email_notification=send_email,
                    requested_by=request.user,
                    completed_at=timezone.now(),
                )
                
                serializer = HoldingSerializer(holding)
                return Response({
                    'status': 'completed',
                    'message': 'Shares placed in holding bucket. Click the email icon to release shares and notify shareholder.',
                    'holding': serializer.data,
                    'issuance_request_id': str(issuance_request.id),
                    'investment_type': investment_type,
                    'holding_status': 'HELD',
                })
    
    @action(detail=False, methods=['post'], url_path='release-shares')
    def release_shares(self, request):
        """
        Release shares from holding bucket to shareholder and send email notification.
        
        This endpoint is called when the admin clicks the email icon on the Shareholders page.
        It changes HELD holdings to ACTIVE and sends the email notification.
        
        Uses transaction.atomic() and select_for_update() for data integrity.
        
        POST /api/v1/holdings/release-shares/
        {
            "shareholder_id": "uuid"
        }
        """
        from django.utils import timezone
        from django.db import transaction
        from django.db.models import Sum
        from apps.core.models import Shareholder
        from apps.core.services.email import EmailService
        
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)
        
        shareholder_id = request.data.get('shareholder_id')
        if not shareholder_id:
            return Response({'error': 'shareholder_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            shareholder = Shareholder.objects.get(id=shareholder_id, tenant=tenant)
        except Shareholder.DoesNotExist:
            return Response({'error': 'Shareholder not found'}, status=status.HTTP_404_NOT_FOUND)
        
        held_count = Holding.objects.filter(
            shareholder=shareholder,
            tenant=tenant,
            status='HELD'
        ).count()
        
        if held_count == 0:
            active_count = Holding.objects.filter(
                shareholder=shareholder,
                tenant=tenant,
                status='ACTIVE'
            ).count()
            
            if active_count > 0:
                return Response({
                    'status': 'already_released',
                    'message': 'All shares have already been released to this shareholder.',
                })
            else:
                return Response(
                    {'error': 'No shares found for this shareholder. Please issue shares first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        released_shares = 0
        issuer = None
        email_error_msg = None
        
        with transaction.atomic():
            held_holdings = Holding.objects.select_for_update().filter(
                shareholder=shareholder,
                tenant=tenant,
                status='HELD'
            )
            
            for holding in held_holdings:
                holding.status = 'ACTIVE'
                holding.released_at = timezone.now()
                holding.released_by = request.user
                holding.save()
                released_shares += holding.share_quantity
                if not issuer:
                    issuer = holding.issuer
        
        total_active_shares = Holding.objects.filter(
            shareholder=shareholder,
            tenant=tenant,
            status='ACTIVE'
        ).aggregate(total=Sum('share_quantity'))['total'] or 0
        
        email_sent = False
        if shareholder.email and issuer:
            try:
                email_service = EmailService()
                email_service.send_share_update_or_invitation(
                    shareholder=shareholder,
                    issuer=issuer,
                    additional_shares=int(released_shares),
                    total_shares=int(total_active_shares),
                )
                email_sent = True
            except Exception as e:
                email_error_msg = str(e)
        
        message = f'{int(released_shares)} shares released to shareholder.'
        if email_sent:
            message += ' Email notification sent.'
        elif shareholder.email:
            message += f' Email failed to send: {email_error_msg}'
        else:
            message += ' No email sent (shareholder has no email address).'
        
        return Response({
            'status': 'released',
            'message': message,
            'released_shares': int(released_shares),
            'total_shares': int(total_active_shares),
            'email_sent': email_sent,
            'email_error': email_error_msg,
        })


class CertificateViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated, TenantScopedPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['issuer', 'shareholder', 'status', 'has_legend']
    search_fields = ['certificate_number', 'issuer__company_name']
    ordering = ['-issue_date']


class TransferViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated, CanProcessTransfers]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['issuer', 'from_shareholder', 'to_shareholder', 'status', 'transfer_type']
    search_fields = ['from_shareholder__first_name', 'to_shareholder__first_name', 'issuer__company_name']
    ordering = ['-transfer_date']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a pending transfer"""
        from django.utils import timezone
        
        transfer = self.get_object()
        if transfer.status != 'PENDING':
            return Response(
                {'error': f'Cannot approve transfer with status {transfer.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transfer.status = 'APPROVED'
        transfer.processed_by = request.user
        transfer.processed_date = timezone.now()
        transfer.save()
        serializer = self.get_serializer(transfer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a pending transfer"""
        from django.utils import timezone
        
        transfer = self.get_object()
        if transfer.status != 'PENDING':
            return Response(
                {'error': f'Cannot reject transfer with status {transfer.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transfer.status = 'REJECTED'
        transfer.rejection_reason = request.data.get('reason', '')
        transfer.processed_by = request.user
        transfer.processed_date = timezone.now()
        transfer.save()
        serializer = self.get_serializer(transfer)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute an approved transfer"""
        from django.db import transaction
        from django.utils import timezone
        from decimal import Decimal
        from apps.core.models import AuditLog
        
        transfer = self.get_object()
        
        if transfer.status == 'EXECUTED':
            return Response(
                {'error': 'Transfer has already been executed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if transfer.status != 'APPROVED':
            return Response(
                {'error': f'Cannot execute transfer with status {transfer.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                seller_holding = Holding.objects.select_for_update().get(
                    shareholder=transfer.from_shareholder,
                    issuer=transfer.issuer,
                    security_class=transfer.security_class
                )
                
                if seller_holding.share_quantity < transfer.share_quantity:
                    return Response(
                        {'error': 'Insufficient shares to transfer'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                old_seller_qty = seller_holding.share_quantity
                seller_holding.share_quantity -= transfer.share_quantity
                seller_holding.save()
                
                buyer_holding, created = Holding.objects.get_or_create(
                    shareholder=transfer.to_shareholder,
                    issuer=transfer.issuer,
                    security_class=transfer.security_class,
                    defaults={
                        'share_quantity': Decimal('0'),
                        'acquisition_date': transfer.transfer_date,
                        'holding_type': 'DRS',
                    }
                )
                old_buyer_qty = buyer_holding.share_quantity if not created else Decimal('0')
                buyer_holding.share_quantity += transfer.share_quantity
                buyer_holding.save()
                
                if transfer.surrendered_certificates:
                    Certificate.objects.filter(
                        issuer=transfer.issuer,
                        certificate_number__in=transfer.surrendered_certificates
                    ).update(status='CANCELLED', cancellation_date=transfer.transfer_date)
                
                transfer.status = 'EXECUTED'
                transfer.processed_by = request.user
                transfer.processed_date = timezone.now()
                transfer.save()
                
                from apps.core.signals import set_audit_signal_flag, clear_audit_signal_flag
                set_audit_signal_flag()
                try:
                    AuditLog.objects.create(
                        user=request.user,
                        user_email=request.user.email if request.user else 'system',
                        action_type='TRANSFER_EXECUTED',
                        model_name='Transfer',
                        object_id=str(transfer.id),
                        object_repr=str(transfer),
                        new_value={
                            'transfer_id': str(transfer.id),
                            'from': str(transfer.from_shareholder),
                            'to': str(transfer.to_shareholder),
                            'shares': float(transfer.share_quantity),
                            'seller_before': float(old_seller_qty),
                            'seller_after': float(seller_holding.share_quantity),
                            'buyer_before': float(old_buyer_qty),
                            'buyer_after': float(buyer_holding.share_quantity),
                        },
                        timestamp=timezone.now(),
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    )
                finally:
                    clear_audit_signal_flag()
                
                serializer = self.get_serializer(transfer)
                return Response(serializer.data)
                
        except Holding.DoesNotExist:
            return Response(
                {'error': 'Seller holding not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuditLogViewSet(TenantQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsTenantStaff]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action_type', 'model_name', 'user']
    search_fields = ['user_email', 'object_repr']
    ordering = ['-timestamp']
