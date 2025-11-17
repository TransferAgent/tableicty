from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.models import Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer, AuditLog
from .serializers import (
    IssuerSerializer, SecurityClassSerializer, ShareholderSerializer,
    HoldingSerializer, CertificateSerializer, TransferSerializer, AuditLogSerializer
)


class IssuerViewSet(viewsets.ModelViewSet):
    queryset = Issuer.objects.all()
    serializer_class = IssuerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['otc_tier', 'tavs_enabled', 'is_active', 'blockchain_enabled']
    search_fields = ['company_name', 'ticker_symbol', 'cusip', 'cik']
    ordering_fields = ['company_name', 'created_at', 'ticker_symbol']
    ordering = ['company_name']
    
    @action(detail=True, methods=['get'])
    def cap_table(self, request, pk=None):
        """Generate cap table for this issuer"""
        issuer = self.get_object()
        holdings = Holding.objects.filter(issuer=issuer).select_related('shareholder', 'security_class')
        
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
        """Get authorized vs issued shares summary"""
        issuer = self.get_object()
        holdings = Holding.objects.filter(issuer=issuer)
        
        total_issued = sum(h.share_quantity for h in holdings)
        
        return Response({
            'authorized_shares': float(issuer.total_authorized_shares),
            'issued_shares': float(total_issued),
            'available_shares': float(issuer.total_authorized_shares - total_issued),
            'utilization_percentage': round(float(total_issued) / float(issuer.total_authorized_shares) * 100, 2)
        })


class SecurityClassViewSet(viewsets.ModelViewSet):
    queryset = SecurityClass.objects.all()
    serializer_class = SecurityClassSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['issuer', 'security_type', 'voting_rights', 'is_active']
    search_fields = ['class_designation', 'issuer__company_name']
    ordering = ['issuer', 'security_type']


class ShareholderViewSet(viewsets.ModelViewSet):
    queryset = Shareholder.objects.all()
    serializer_class = ShareholderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['account_type', 'accredited_investor', 'kyc_verified', 'is_active', 'country']
    search_fields = ['first_name', 'last_name', 'entity_name', 'email']
    ordering = ['last_name', 'first_name']
    
    @action(detail=True, methods=['get'])
    def holdings(self, request, pk=None):
        """Get all holdings for this shareholder"""
        shareholder = self.get_object()
        holdings = Holding.objects.filter(shareholder=shareholder).select_related('issuer', 'security_class')
        serializer = HoldingSerializer(holdings, many=True)
        return Response(serializer.data)


class HoldingViewSet(viewsets.ModelViewSet):
    queryset = Holding.objects.all()
    serializer_class = HoldingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['shareholder', 'issuer', 'security_class', 'holding_type', 'is_restricted']
    search_fields = ['shareholder__first_name', 'shareholder__last_name', 'issuer__company_name']
    ordering = ['issuer', '-share_quantity']


class CertificateViewSet(viewsets.ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['issuer', 'shareholder', 'status', 'has_legend']
    search_fields = ['certificate_number', 'issuer__company_name']
    ordering = ['-issue_date']


class TransferViewSet(viewsets.ModelViewSet):
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer
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


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action_type', 'model_name', 'user']
    search_fields = ['user_email', 'object_repr']
    ordering = ['-timestamp']
