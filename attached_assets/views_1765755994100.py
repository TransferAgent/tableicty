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


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def seed_user_data_view(request):
    """
    Secure endpoint to seed test data for the authenticated user's shareholder account.
    Only creates data for the requesting user - cannot seed for others.
    """
    from apps.core.models import Issuer, SecurityClass
    from decimal import Decimal
    from datetime import date, timedelta
    import random
    
    shareholder = request.user.shareholder
    
    # Check if user already has holdings (prevent duplicate seeding)
    existing_holdings = Holding.objects.filter(shareholder=shareholder).count()
    if existing_holdings > 0:
        return Response({
            'error': 'User already has data. Cannot seed again.',
            'existing_holdings': existing_holdings
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get existing issuers and security classes
    issuers = list(Issuer.objects.filter(is_active=True)[:3])
    if not issuers:
        return Response({
            'error': 'No issuers found in database. Please seed issuers first.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    holdings_created = 0
    transfers_created = 0
    
    # Create holdings for each issuer
    for issuer in issuers:
        security_classes = SecurityClass.objects.filter(issuer=issuer, is_active=True)
        for sec_class in security_classes[:1]:  # One holding per issuer
            share_qty = Decimal(random.randint(1000, 50000))
            holding = Holding.objects.create(
                shareholder=shareholder,
                issuer=issuer,
                security_class=sec_class,
                share_quantity=share_qty,
                acquisition_date=date.today() - timedelta(days=random.randint(30, 365)),
                acquisition_price=Decimal(str(round(random.uniform(0.50, 5.00), 4))),
                holding_type=random.choice(['DRS', 'CERTIFICATE']),
                is_restricted=False
            )
            holdings_created += 1
            
            # Create transfer records for this holding
            for i in range(random.randint(2, 4)):
                transfer_qty = Decimal(random.randint(100, int(share_qty / 5)))
                transfer = Transfer.objects.create(
                    issuer=issuer,
                    security_class=sec_class,
                    from_shareholder=None,
                    to_shareholder=shareholder,
                    share_quantity=transfer_qty,
                    transfer_type=random.choice(['PURCHASE', 'GIFT', 'INHERITANCE']),
                    transfer_date=date.today() - timedelta(days=random.randint(1, 180)),
                    price_per_share=Decimal(str(round(random.uniform(0.50, 5.00), 4))),
                    status='COMPLETED',
                    approved_by='System',
                    approved_date=date.today() - timedelta(days=random.randint(1, 30))
                )
                transfers_created += 1
    
    # Create tax document audit log entries
    tax_docs_created = 0
    for year in [2023, 2024]:
        from apps.core.signals import set_audit_signal_flag, clear_audit_signal_flag
        set_audit_signal_flag()
        try:
            AuditLog.objects.create(
                model_name='TAX_DOCUMENT',
                object_id=str(uuid.uuid4()),
                action_type='CREATE',
                user=request.user,
                user_email=request.user.email,
                object_repr=f"1099-DIV {year}",
                new_value={
                    'document_type': '1099-DIV',
                    'tax_year': year,
                    'status': 'AVAILABLE',
                    'generated_date': f"{year}-01-31",
                    'shareholder_id': str(shareholder.id)
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            tax_docs_created += 1
        finally:
            clear_audit_signal_flag()
    
    return Response({
        'message': 'Test data seeded successfully',
        'data_created': {
            'holdings': holdings_created,
            'transfers': transfers_created,
            'tax_documents': tax_docs_created
        },
        'shareholder_email': shareholder.email
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_shareholder_view(request):
    """
    TEMPORARY endpoint to create a Shareholder record before registration.
    Requires a secret key for security. REMOVE AFTER USE.
    """
    import os
    ADMIN_SECRET = os.environ.get('ADMIN_SETUP_SECRET', '')
    
    if not ADMIN_SECRET:
        return Response({'error': 'Admin secret not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    secret = request.data.get('secret')
    if secret != ADMIN_SECRET:
        return Response({'error': 'Invalid secret key'}, status=status.HTTP_403_FORBIDDEN)
    
    email = request.data.get('email')
    first_name = request.data.get('first_name', 'Admin')
    last_name = request.data.get('last_name', 'User')
    account_type = request.data.get('account_type', 'INDIVIDUAL')
    
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if Shareholder.objects.filter(email=email).exists():
        existing = Shareholder.objects.get(email=email)
        return Response({
            'status': 'already_exists',
            'shareholder_id': str(existing.id),
            'email': existing.email,
            'message': 'Shareholder already exists. You can proceed to register.'
        }, status=status.HTTP_200_OK)
    
    shareholder = Shareholder.objects.create(
        email=email,
        account_type=account_type,
        first_name=first_name,
        last_name=last_name,
        is_active=True
    )
    
    return Response({
        'status': 'success',
        'shareholder_id': str(shareholder.id),
        'email': shareholder.email,
        'message': 'Shareholder created. You can now register on the frontend.'
    }, status=status.HTTP_201_CREATED)




@api_view(['POST'])
@permission_classes([AllowAny])
def create_shareholder_view(request):
    """
    TEMPORARY endpoint to create a Shareholder record before registration.
    Requires a secret key for security. REMOVE AFTER USE.
    """
    import os
    ADMIN_SECRET = os.environ.get('ADMIN_SETUP_SECRET', '')
    
    if not ADMIN_SECRET:
        return Response({'error': 'Admin secret not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    secret = request.data.get('secret')
    if secret != ADMIN_SECRET:
        return Response({'error': 'Invalid secret key'}, status=status.HTTP_403_FORBIDDEN)
    
    email = request.data.get('email')
    first_name = request.data.get('first_name', 'Admin')
    last_name = request.data.get('last_name', 'User')
    account_type = request.data.get('account_type', 'INDIVIDUAL')
    
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    if Shareholder.objects.filter(email=email).exists():
        existing = Shareholder.objects.get(email=email)
        return Response({
            'status': 'already_exists',
            'shareholder_id': str(existing.id),
            'email': existing.email,
            'message': 'Shareholder already exists. You can proceed to register.'
        }, status=status.HTTP_200_OK)
    
    shareholder = Shareholder.objects.create(
        email=email,
        account_type=account_type,
        first_name=first_name,
        last_name=last_name,
        is_active=True
    )
    
    return Response({
        'status': 'success',
        'shareholder_id': str(shareholder.id),
        'email': shareholder.email,
        'message': 'Shareholder created. You can now register on the frontend.'
    }, status=status.HTTP_201_CREATED)


