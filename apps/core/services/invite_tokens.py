"""
JWT-based invite token service for shareholder invitations.
"""
import hashlib
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, Tuple
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.exceptions import TokenError

logger = logging.getLogger(__name__)


class ShareholderInviteToken(Token):
    """
    Custom JWT token for shareholder invitations.
    7-day expiry, contains shareholder_id, email, tenant_id, role.
    """
    token_type = 'shareholder_invite'
    lifetime = timedelta(days=7)
    
    @classmethod
    def for_shareholder(
        cls,
        shareholder_id: str,
        email: str,
        tenant_id: str,
        company_id: str,
        company_name: str,
        share_count: int = 0,
        share_class: str = '',
        role: str = 'SHAREHOLDER',
    ) -> 'ShareholderInviteToken':
        """
        Create an invite token for a shareholder.
        
        Args:
            shareholder_id: UUID of the shareholder record
            email: Shareholder's email address
            tenant_id: UUID of the tenant
            company_id: UUID of the issuer/company
            company_name: Name of the issuing company
            share_count: Number of shares issued (for display)
            share_class: Class of shares issued
            role: Role to assign upon registration
            
        Returns:
            ShareholderInviteToken instance
        """
        token = cls()
        token['shareholder_id'] = str(shareholder_id)
        token['email'] = email
        token['tenant_id'] = str(tenant_id)
        token['company_id'] = str(company_id)
        token['company_name'] = company_name
        token['share_count'] = share_count
        token['share_class'] = share_class
        token['role'] = role
        
        return token
    
    def get_token_hash(self) -> str:
        """
        Generate a hash of the token for storage/revocation checking.
        """
        return hashlib.sha256(str(self).encode()).hexdigest()[:64]


def create_invite_token(
    shareholder_id: str,
    email: str,
    tenant_id: str,
    company_id: str,
    company_name: str,
    share_count: int = 0,
    share_class: str = '',
) -> Tuple[str, str, 'timezone.datetime']:
    """
    Create a JWT invite token and return token string, hash, and expiry.
    
    Returns:
        Tuple of (token_string, token_hash, expires_at)
    """
    token = ShareholderInviteToken.for_shareholder(
        shareholder_id=shareholder_id,
        email=email,
        tenant_id=tenant_id,
        company_id=company_id,
        company_name=company_name,
        share_count=share_count,
        share_class=share_class,
    )
    
    token_string = str(token)
    token_hash = token.get_token_hash()
    expires_at = timezone.now() + ShareholderInviteToken.lifetime
    
    return token_string, token_hash, expires_at


def validate_invite_token(token_string: str, check_database: bool = True) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Validate an invite token and extract its payload.
    Also verifies the token hasn't been revoked by checking database.
    
    Args:
        token_string: The JWT token string
        check_database: Whether to verify token hash against TenantInvitation (default True)
        
    Returns:
        Tuple of (is_valid, payload_dict, error_message)
    """
    try:
        token = ShareholderInviteToken(token_string)
        
        if token['token_type'] != 'shareholder_invite':
            return False, None, 'Invalid token type'
        
        token_hash = hashlib.sha256(token_string.encode()).hexdigest()[:64]
        
        if check_database:
            from apps.core.models import TenantInvitation
            invitation = TenantInvitation.objects.filter(
                token=token_hash,
                status='PENDING'
            ).first()
            
            if not invitation:
                return False, None, 'Invitation not found or already used/revoked'
            
            if not invitation.is_valid():
                return False, None, 'Invitation has expired'
        
        payload = {
            'shareholder_id': token.get('shareholder_id'),
            'email': token.get('email'),
            'tenant_id': token.get('tenant_id'),
            'company_id': token.get('company_id'),
            'company_name': token.get('company_name'),
            'share_count': token.get('share_count', 0),
            'share_class': token.get('share_class', ''),
            'role': token.get('role', 'SHAREHOLDER'),
            'token_hash': token_hash,
        }
        
        return True, payload, None
        
    except TokenError as e:
        logger.warning(f"Invalid invite token: {str(e)}")
        return False, None, str(e)
    except Exception as e:
        logger.error(f"Error validating invite token: {str(e)}")
        return False, None, 'Token validation failed'
