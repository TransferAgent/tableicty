from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.models import Shareholder, Holding, Transfer, AuditLog
from .serializers import (
    ShareholderRegistrationSerializer,
    ShareholderProfileSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
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
