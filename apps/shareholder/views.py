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
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)


class ShareholderLoginView(TokenObtainPairView):
    pass


class ShareholderLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def shareholder_holdings_view(request):
    shareholder = request.user.shareholder
    holdings = Holding.objects.filter(shareholder=shareholder, is_active=True).select_related('issuer', 'security_class').order_by('-acquisition_date')
    holdings_data = [{
        'id': str(h.id),
        'issuer': {'name': h.issuer.company_name, 'ticker': h.issuer.ticker_symbol, 'otc_tier': h.issuer.otc_tier},
        'security_class': {'type': h.security_class.security_type, 'designation': h.security_class.class_designation},
        'share_quantity': str(h.share_quantity),
        'acquisition_date': h.acquisition_date.isoformat() if h.acquisition_date else None,
        'holding_type': h.holding_type,
        'percentage_ownership': round((float(h.share_quantity) / float(h.security_class.authorized_shares) * 100), 4) if h.security_class.authorized_shares > 0 else 0
    } for h in holdings]
    return Response({'count': len(holdings_data), 'holdings': holdings_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsShareholderOwner])
def shareholder_summary_view(request):
    shareholder = request.user.shareholder
    holdings = Holding.objects.filter(shareholder=shareholder, is_active=True)
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
    holdings = Holding.objects.filter(shareholder=shareholder, is_active=True).select_related('issuer')
    
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
    
    certificate_id = str(data['certificate'].id) if 'certificate' in data else ''
    request_id = str(uuid.uuid4())
    
    AuditLog.objects.create(
        model_name='CERTIFICATE_CONVERSION',
        object_id=certificate_id,
        action_type='CREATE',
        user=request.user,
        user_email=request.user.email,
        object_repr=f"Certificate Conversion Request {request_id}",
        new_value={
            'request_id': request_id,
            'conversion_type': data['conversion_type'],
            'certificate_number': data['certificate_number'],
            'issuer_id': str(data['issuer_id']),
            'shareholder_id': str(shareholder.id),
            'notes': data.get('notes', '')
        },
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
    )
    
    return Response({
        'message': 'Certificate conversion request submitted successfully',
        'request_id': request_id,
        'status': 'PENDING',
        'estimated_completion': '5-7 business days',
        'note': 'Our transfer agent team will review your request and contact you if additional information is needed.'
    }, status=status.HTTP_201_CREATED)


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
