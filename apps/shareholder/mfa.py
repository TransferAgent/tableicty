"""
MFA (Multi-Factor Authentication) views using django-otp TOTP.

Provides endpoints for:
- Setting up TOTP device (QR code generation)
- Verifying TOTP code during enrollment
- Verifying TOTP code during login (2FA step)
"""
import base64
import io
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_otp.plugins.otp_totp.models import TOTPDevice

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mfa_status_view(request):
    """Check if user has MFA enabled and verified."""
    user = request.user
    devices = TOTPDevice.objects.filter(user=user)
    
    has_device = devices.exists()
    has_confirmed_device = devices.filter(confirmed=True).exists()
    
    return Response({
        'mfa_enabled': has_confirmed_device,
        'mfa_pending_setup': has_device and not has_confirmed_device,
        'device_count': devices.count(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_setup_view(request):
    """
    Setup MFA for the authenticated user.
    
    Creates a new TOTP device and returns the provisioning URI and QR code.
    The device is NOT confirmed until the user verifies with a valid code.
    """
    user = request.user
    
    existing_confirmed = TOTPDevice.objects.filter(user=user, confirmed=True).exists()
    if existing_confirmed:
        return Response(
            {'error': 'MFA is already enabled. Disable it first to set up a new device.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    TOTPDevice.objects.filter(user=user, confirmed=False).delete()
    
    device = TOTPDevice.objects.create(
        user=user,
        name=f'tableicty-{user.email}',
        confirmed=False,
    )
    
    issuer = 'tableicty'
    provisioning_uri = device.config_url
    
    response_data = {
        'message': 'MFA device created. Scan the QR code and verify with a code.',
        'provisioning_uri': provisioning_uri,
        'device_name': device.name,
    }
    
    if HAS_QRCODE:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        qr_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        response_data['qr_code_base64'] = f'data:image/png;base64,{qr_base64}'
    
    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_verify_setup_view(request):
    """
    Verify the TOTP code to confirm MFA setup.
    
    Once verified, the device is confirmed and MFA is active.
    """
    user = request.user
    code = request.data.get('code', '').strip()
    
    if not code:
        return Response(
            {'error': 'Verification code is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(code) != 6 or not code.isdigit():
        return Response(
            {'error': 'Code must be exactly 6 digits.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if not device:
        return Response(
            {'error': 'No pending MFA device found. Please start setup again.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if device.verify_token(code):
        device.confirmed = True
        device.save()
        
        return Response({
            'message': 'MFA enabled successfully.',
            'mfa_enabled': True,
        })
    else:
        return Response(
            {'error': 'Invalid verification code. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_verify_login_view(request):
    """
    Verify TOTP code during login (2FA step).
    
    Called after initial password authentication if MFA is enabled.
    Returns a new access token with mfa_verified claim set to True.
    """
    user = request.user
    code = request.data.get('code', '').strip()
    
    if not code:
        return Response(
            {'error': 'Verification code is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if not device:
        return Response(
            {'error': 'MFA is not enabled for this account.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if device.verify_token(code):
        from rest_framework_simplejwt.tokens import RefreshToken
        from .jwt import get_tokens_for_user_with_mfa
        
        tokens = get_tokens_for_user_with_mfa(user, mfa_verified=True)
        
        response = Response({
            'message': 'MFA verification successful.',
            'access': tokens['access'],
            'mfa_verified': True,
        })
        
        cookie_settings = settings.REFRESH_TOKEN_COOKIE_SETTINGS
        response.set_cookie(
            key=cookie_settings['key'],
            value=tokens['refresh'],
            path=cookie_settings['path'],
            domain=cookie_settings['domain'],
            httponly=cookie_settings['httponly'],
            secure=cookie_settings['secure'],
            samesite=cookie_settings['samesite'],
            max_age=cookie_settings['max_age']
        )
        
        return response
    else:
        return Response(
            {'error': 'Invalid verification code.'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mfa_disable_view(request):
    """
    Disable MFA for the authenticated user.
    
    Requires both password AND current TOTP code for security.
    This prevents attackers with stolen passwords from disabling MFA.
    """
    user = request.user
    password = request.data.get('password', '')
    code = request.data.get('code', '').strip()
    
    if not password:
        return Response(
            {'error': 'Password is required to disable MFA.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not code:
        return Response(
            {'error': 'TOTP code is required to disable MFA.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not user.check_password(password):
        return Response(
            {'error': 'Incorrect password.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if not device:
        return Response(
            {'error': 'MFA is not enabled for this account.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not device.verify_token(code):
        return Response(
            {'error': 'Invalid TOTP code.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    deleted_count, _ = TOTPDevice.objects.filter(user=user).delete()
    
    if deleted_count > 0:
        from .jwt import get_tokens_for_user_with_mfa
        tokens = get_tokens_for_user_with_mfa(user, mfa_verified=False)
        
        response = Response({
            'message': 'MFA disabled successfully.',
            'mfa_enabled': False,
            'access': tokens['access'],
        })
        
        cookie_settings = settings.REFRESH_TOKEN_COOKIE_SETTINGS
        response.set_cookie(
            key=cookie_settings['key'],
            value=tokens['refresh'],
            path=cookie_settings['path'],
            domain=cookie_settings['domain'],
            httponly=cookie_settings['httponly'],
            secure=cookie_settings['secure'],
            samesite=cookie_settings['samesite'],
            max_age=cookie_settings['max_age']
        )
        
        return response
    else:
        return Response(
            {'error': 'MFA was not enabled.'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mfa_backup_codes_view(request):
    """
    Generate backup codes for MFA recovery.
    
    Note: This is a placeholder. In production, implement proper backup code
    storage using django-otp's static device or a custom solution.
    """
    return Response({
        'message': 'Backup codes feature coming soon.',
        'backup_codes': [],
    })
