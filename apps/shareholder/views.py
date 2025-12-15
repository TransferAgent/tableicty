from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.db import models
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
import uuid

from apps.core.models import Shareholder, Holding, Transfer, AuditLog
from .serializers import (
    ShareholderRegistrationSerializer,
    ShareholderProfileSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    TransferSerializer,
    TaxDocumentSerializer,
    CertificateConversionRequestSerializer,
    ProfileUpdateSerializer,
)
from .permissions import IsShareholderOwner


class ShareholderRegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ShareholderRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        
        response = Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)
        
        cookie_settings = settings.REFRESH_TOKEN_COOKIE_SETTINGS
        response.set_cookie(
            key=cookie_settings['key'],
            value=str(refresh),
            path=cookie_settings['path'],
            domain=cookie_settings['domain'],
            httponly=cookie_settings['httponly'],
            secure=cookie_settings['secure'],
            samesite=cookie_settings['samesite'],
            max_age=cookie_settings['max_age']
        )
        
        return response


class ShareholderLoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            refresh_token = response.data.get('refresh')
            
            if refresh_token:
                cookie_settings = settings.REFRESH_TOKEN_COOKIE_SETTINGS
                response.set_cookie(
                    key=cookie_settings['key'],
                    value=refresh_token,
                    path=cookie_settings['path'],
                    domain=cookie_settings['domain'],
                    httponly=cookie_settings['httponly'],
                    secure=cookie_settings['secure'],
                    samesite=cookie_settings['samesite'],
                    max_age=cookie_settings['max_age']
                )
                
                del response.data['refresh']
        
        return response


class ShareholderTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        
        if refresh_token:
            if hasattr(request.data, '_mutable'):
                request.data._mutable = True
                request.data['refresh'] = refresh_token
                request.data._mutable = False
            else:
                request.data['refresh'] = refresh_token
        
        return super().post(request, *args, **kwargs)


class ShareholderLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        response = Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        cookie_settings = settings.REFRESH_TOKEN_COOKIE_SETTINGS
        
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception as e:
            pass
        
        response.delete_cookie(
            key=cookie_settings['key'],
            path=cookie_settings['path'],
            domain=cookie_settings['domain'],
            samesite=cookie_settings['samesite']
        )
        return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def shareholder_holdings_view(request):
    shareholder = request.user.shareholder
    holdings = Holding.objects.filter(shareholder=shareholder).select_related('issuer', 'security_class').order_by('-acquisition_date')
    holdings_data = [{
        'id': str(h.id),
        'issuer': {'name': h.issuer.company_name, 'ticker': h.issuer.ticker_symbol, 'otc_tier': h.issuer.otc_tier},
        'security_class': {'type': h.security_class.security_type, 'designation': h.security_class.class_designation},
        'share_quantity': str(int(h.share_quantity)) if h.share_quantity == int(h.share_quantity) else str(h.share_quantity),
        'acquisition_date': h.acquisition_date.isoformat() if h.acquisition_date else None,
        'holding_type': h.holding_type,
        'percentage_ownership': round((float(h.share_quantity) / float(h.security_class.shares_authorized) * 100), 4) if h.security_class.shares_authorized > 0 else 0
    } for h in holdings]
    return Response({'count': len(holdings_data), 'holdings': holdings_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def shareholder_summary_view(request):
    shareholder = request.user.shareholder
    holdings = Holding.objects.filter(shareholder=shareholder)
    total_companies = holdings.values('issuer').distinct().count()
    total_shares = sum(float(h.share_quantity) for h in holdings)
    return Response({'total_companies': total_companies, 'total_shares': total_shares, 'total_holdings': holdings.count()})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def transaction_history_view(request):
    shareholder = request.user.shareholder
    transfers = Transfer.objects.filter(
        models.Q(from_shareholder=shareholder) | models.Q(to_shareholder=shareholder)
    ).select_related('issuer', 'security_class', 'from_shareholder', 'to_shareholder').order_by('-transfer_date')
    
    transfer_type = request.query_params.get('transfer_type')
    status_filter = request.query_params.get('status')
    year = request.query_params.get('year')
    
    if transfer_type:
        transfers = transfers.filter(transfer_type=transfer_type)
    if status_filter:
        transfers = transfers.filter(status=status_filter)
    if year:
        try:
            year_int = int(year)
            transfers = transfers.filter(transfer_date__year=year_int)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid year parameter'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = TransferSerializer(transfers, many=True, context={'request': request})
    return Response({
        'count': transfers.count(),
        'transfers': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def tax_documents_view(request):
    from datetime import date
    shareholder = request.user.shareholder
    holdings = Holding.objects.filter(shareholder=shareholder).select_related('issuer')
    
    documents = []
    current_year = date.today().year
    
    for holding in holdings:
        for year in range(current_year - 2, current_year + 1):
            documents.append({
                'id': f"{holding.issuer.id}-{year}",
                'document_type': '1099-DIV',
                'tax_year': year,
                'issuer_name': holding.issuer.company_name,
                'issuer_ticker': holding.issuer.ticker_symbol or 'N/A',
                'generated_date': date(year, 12, 31),
                'status': 'AVAILABLE' if year < current_year else 'PENDING',
                'download_url': f"/api/v1/shareholder/tax-documents/{holding.issuer.id}-{year}/download/"
            })
    
    serializer = TaxDocumentSerializer(documents, many=True)
    return Response({
        'count': len(documents),
        'documents': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def tax_document_download_view(request, doc_id):
    """Download a tax document as PDF"""
    from django.http import HttpResponse
    from datetime import date
    
    shareholder = request.user.shareholder
    
    try:
        parts = doc_id.rsplit('-', 1)
        if len(parts) != 2:
            return Response({'error': 'Invalid document ID'}, status=status.HTTP_400_BAD_REQUEST)
        
        issuer_id, year_str = parts
        year = int(year_str)
    except (ValueError, IndexError):
        return Response({'error': 'Invalid document ID format'}, status=status.HTTP_400_BAD_REQUEST)
    
    holding = Holding.objects.filter(
        shareholder=shareholder,
        issuer_id=issuer_id
    ).select_related('issuer').first()
    
    if not holding:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
    
    current_year = date.today().year
    if year >= current_year:
        return Response({'error': 'Document not yet available'}, status=status.HTTP_400_BAD_REQUEST)
    
    content = f"""
================================================================================
                            FORM 1099-DIV
                    Dividends and Distributions
                          Tax Year {year}
================================================================================

PAYER'S Information:
  Name: {holding.issuer.company_name}
  Ticker: {holding.issuer.ticker_symbol or 'N/A'}

RECIPIENT'S Information:
  Name: {shareholder.first_name} {shareholder.last_name}
  Account: ****{str(shareholder.id)[-4:]}

================================================================================

Box 1a - Total ordinary dividends:             $0.00
Box 1b - Qualified dividends:                  $0.00
Box 2a - Total capital gain distributions:     $0.00
Box 3  - Nondividend distributions:            $0.00

================================================================================

Shares Held: {holding.share_quantity}

--------------------------------------------------------------------------------
This is a placeholder document for demonstration purposes.
Actual 1099-DIV forms are generated annually by the transfer agent
and will be available in late January following the tax year.
--------------------------------------------------------------------------------

Generated: {date.today().isoformat()}
Document ID: {doc_id}
================================================================================
"""
    
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="1099-DIV_{year}_{holding.issuer.ticker_symbol or "STOCK"}.txt"'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def certificate_conversion_request_view(request):
    serializer = CertificateConversionRequestSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    shareholder = request.user.shareholder
    data = serializer.validated_data
    holding = data['holding']
    
    request_id = str(uuid.uuid4())
    
    from apps.core.signals import set_audit_signal_flag, clear_audit_signal_flag
    set_audit_signal_flag()
    try:
        AuditLog.objects.create(
            model_name='CERTIFICATE_CONVERSION',
            object_id=str(holding.id),
            action_type='CREATE',
            user=request.user,
            user_email=request.user.email,
            object_repr=f"Certificate Conversion Request {request_id}",
            new_value={
                'request_id': request_id,
                'conversion_type': data['conversion_type'],
                'holding_id': str(holding.id),
                'issuer_name': holding.issuer.company_name,
                'share_quantity': data['share_quantity'],
                'shareholder_id': str(shareholder.id),
                'mailing_address': data.get('mailing_address', '')
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
    finally:
        clear_audit_signal_flag()
    
    return Response({
        'message': 'Certificate conversion request submitted successfully',
        'request_id': request_id,
        'status': 'PENDING',
        'estimated_completion': '5-7 business days',
        'note': 'Our transfer agent team will review your request and contact you if additional information is needed.'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def certificate_requests_list_view(request):
    """List certificate conversion requests for the authenticated shareholder"""
    shareholder = request.user.shareholder
    
    # Get certificate conversion requests from AuditLog
    from apps.core.models import AuditLog
    audit_logs = AuditLog.objects.filter(
        model_name='CERTIFICATE_CONVERSION',
        user=request.user
    ).order_by('-timestamp')
    
    requests = []
    for log in audit_logs:
        new_value = log.new_value or {}
        requests.append({
            'id': new_value.get('request_id', str(log.id)),
            'created_at': log.timestamp.isoformat(),
            'conversion_type': new_value.get('conversion_type', ''),
            'share_quantity': new_value.get('share_quantity', 0),
            'issuer_name': new_value.get('issuer_name', ''),
            'security_type': 'Common Stock',
            'status': 'PENDING',
            'mailing_address': new_value.get('mailing_address', '')
        })
    
    return Response(requests)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def profile_management_view(request):
    shareholder = request.user.shareholder
    
    if request.method == 'GET':
        serializer = ShareholderProfileSerializer(shareholder)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = ProfileUpdateSerializer(shareholder, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        shareholder = serializer.save()
        
        # Return the updated profile data directly (REST standard)
        response_serializer = ShareholderProfileSerializer(shareholder)
        return Response(response_serializer.data)


