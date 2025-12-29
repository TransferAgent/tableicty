"""
Subscription validation and feature gating service.
Provides centralized logic for checking subscription limits and feature access.
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.response import Response

from apps.core.models import Tenant, Subscription, Shareholder, TenantMembership


FEATURE_FLAGS = {
    'email_invitations': {
        'tiers': ['GROWTH', 'ENTERPRISE'],
        'name': 'Email Invitations',
        'upgrade_message': 'Email invitations require Professional plan or higher',
    },
    'certificate_management': {
        'tiers': ['ENTERPRISE'],
        'name': 'Certificate Management',
        'upgrade_message': 'Certificate management is an Enterprise feature',
    },
    'transfer_processing': {
        'tiers': ['GROWTH', 'ENTERPRISE'],
        'name': 'Transfer Processing',
        'upgrade_message': 'Transfer processing requires Professional plan or higher',
    },
    'compliance_reports': {
        'tiers': ['GROWTH', 'ENTERPRISE'],
        'name': 'Compliance Reports',
        'upgrade_message': 'Compliance reports require Professional plan or higher',
    },
    'dtcc_integration': {
        'tiers': ['ENTERPRISE'],
        'name': 'DTCC Integration',
        'upgrade_message': 'DTCC integration is an Enterprise feature',
    },
    'api_access': {
        'tiers': ['ENTERPRISE'],
        'name': 'API Access',
        'upgrade_message': 'API access is an Enterprise feature',
    },
    'priority_support': {
        'tiers': ['ENTERPRISE'],
        'name': 'Priority Support',
        'upgrade_message': 'Priority support is an Enterprise feature',
    },
}


class SubscriptionValidator:
    """
    Validates subscription limits and feature access for tenants.
    """
    
    @staticmethod
    def get_subscription(tenant: Tenant) -> Subscription:
        """Get the subscription for a tenant, or None if not found."""
        try:
            return Subscription.objects.select_related('plan').get(tenant=tenant)
        except Subscription.DoesNotExist:
            return None
    
    @staticmethod
    def get_current_shareholder_count(tenant: Tenant) -> int:
        """Get the current number of shareholders for a tenant."""
        return Shareholder.objects.filter(tenant=tenant).count()
    
    @staticmethod
    def get_current_admin_count(tenant: Tenant) -> int:
        """Get the current number of admin users for a tenant."""
        return TenantMembership.objects.filter(
            tenant=tenant,
            role__in=['TENANT_ADMIN', 'TENANT_STAFF']
        ).count()
    
    @classmethod
    def check_shareholder_limit(cls, tenant: Tenant) -> tuple:
        """
        Check if the tenant can add more shareholders.
        Returns (can_add: bool, current: int, limit: int, message: str)
        """
        subscription = cls.get_subscription(tenant)
        if not subscription or not subscription.plan:
            return True, 0, -1, "No subscription limit"
        
        current = cls.get_current_shareholder_count(tenant)
        limit = subscription.plan.max_shareholders
        
        if limit == -1:
            return True, current, -1, "Unlimited shareholders"
        
        if current >= limit:
            return False, current, limit, f"Shareholder limit reached ({current}/{limit}). Upgrade to add more."
        
        return True, current, limit, f"{current}/{limit} shareholders used"
    
    @classmethod
    def check_admin_limit(cls, tenant: Tenant) -> tuple:
        """
        Check if the tenant can add more admin users.
        Returns (can_add: bool, current: int, limit: int, message: str)
        """
        subscription = cls.get_subscription(tenant)
        if not subscription or not subscription.plan:
            return True, 0, -1, "No subscription limit"
        
        current = cls.get_current_admin_count(tenant)
        limit = subscription.plan.max_users
        
        if limit == -1:
            return True, current, -1, "Unlimited admin users"
        
        if current >= limit:
            return False, current, limit, f"Admin user limit reached ({current}/{limit}). Upgrade to add more."
        
        return True, current, limit, f"{current}/{limit} admin users"
    
    @classmethod
    def has_feature(cls, tenant: Tenant, feature: str) -> bool:
        """Check if a tenant has access to a specific feature."""
        subscription = cls.get_subscription(tenant)
        if not subscription or not subscription.plan:
            return False
        
        if subscription.status not in ['ACTIVE', 'TRIALING']:
            return False
        
        tier = subscription.plan.tier
        
        if feature in FEATURE_FLAGS:
            return tier in FEATURE_FLAGS[feature]['tiers']
        
        features_list = subscription.plan.features or []
        return feature in features_list
    
    @classmethod
    def get_feature_info(cls, tenant: Tenant, feature: str) -> dict:
        """Get detailed info about a feature for a tenant."""
        has_access = cls.has_feature(tenant, feature)
        feature_config = FEATURE_FLAGS.get(feature, {})
        
        return {
            'feature': feature,
            'enabled': has_access,
            'name': feature_config.get('name', feature),
            'upgrade_message': feature_config.get('upgrade_message', 'Feature requires upgrade'),
            'required_tiers': feature_config.get('tiers', []),
        }
    
    @classmethod
    def get_usage_summary(cls, tenant: Tenant) -> dict:
        """Get a complete usage summary for a tenant."""
        subscription = cls.get_subscription(tenant)
        
        if not subscription or not subscription.plan:
            return {
                'tier': None,
                'tier_name': 'No Plan',
                'status': 'INACTIVE',
                'shareholders': {'current': 0, 'limit': 0, 'unlimited': False},
                'admins': {'current': 0, 'limit': 0, 'unlimited': False},
                'features': {},
            }
        
        plan = subscription.plan
        shareholder_can_add, shareholder_current, shareholder_limit, _ = cls.check_shareholder_limit(tenant)
        admin_can_add, admin_current, admin_limit, _ = cls.check_admin_limit(tenant)
        
        features = {}
        for feature_key in FEATURE_FLAGS.keys():
            features[feature_key] = cls.has_feature(tenant, feature_key)
        
        return {
            'tier': plan.tier,
            'tier_name': plan.name,
            'status': subscription.status,
            'price_monthly': str(plan.price_monthly),
            'shareholders': {
                'current': shareholder_current,
                'limit': shareholder_limit,
                'unlimited': shareholder_limit == -1,
                'can_add': shareholder_can_add,
            },
            'admins': {
                'current': admin_current,
                'limit': admin_limit,
                'unlimited': admin_limit == -1,
                'can_add': admin_can_add,
            },
            'features': features,
        }


def require_feature(feature: str):
    """
    Decorator for DRF views that requires a specific subscription feature.
    Returns 403 Forbidden if the tenant doesn't have the feature.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            tenant = getattr(request.user, 'current_tenant', None)
            if not tenant:
                membership = TenantMembership.objects.filter(user=request.user).first()
                tenant = membership.tenant if membership else None
            
            if not tenant:
                return Response(
                    {'error': 'No tenant found for user'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if not SubscriptionValidator.has_feature(tenant, feature):
                feature_info = SubscriptionValidator.get_feature_info(tenant, feature)
                return Response(
                    {
                        'error': 'Feature requires upgrade',
                        'feature': feature,
                        'message': feature_info['upgrade_message'],
                        'upgrade_url': '/pricing',
                        'current_tier': SubscriptionValidator.get_subscription(tenant).plan.tier if SubscriptionValidator.get_subscription(tenant) else None,
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def check_shareholder_limit(tenant: Tenant) -> bool:
    """
    Convenience function to check shareholder limit.
    Returns True if can add, raises PermissionDenied if limit reached.
    """
    can_add, current, limit, message = SubscriptionValidator.check_shareholder_limit(tenant)
    if not can_add:
        raise PermissionDenied(message)
    return True


def check_admin_limit(tenant: Tenant) -> bool:
    """
    Convenience function to check admin user limit.
    Returns True if can add, raises PermissionDenied if limit reached.
    """
    can_add, current, limit, message = SubscriptionValidator.check_admin_limit(tenant)
    if not can_add:
        raise PermissionDenied(message)
    return True
