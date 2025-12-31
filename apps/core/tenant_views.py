"""
Tenant management API views.

Provides endpoints for:
- Tenant self-registration (onboarding)
- Tenant settings management
- User invitation workflow
- Email testing and shareholder invitations
"""
import logging
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import (
    Tenant, TenantMembership, SubscriptionPlan, Subscription, TenantInvitation,
    Shareholder, Holding, Issuer
)
from apps.core.permissions import IsTenantAdmin, CanManageUsers, IsPlatformAdmin
from apps.core.serializers import (
    TenantRegistrationSerializer, TenantSerializer, TenantMembershipSerializer,
    TenantInvitationSerializer, TenantInvitationCreateSerializer,
    AcceptInvitationSerializer
)
from apps.core.services.email import EmailService
from apps.core.services.invite_tokens import create_invite_token, validate_invite_token
from apps.core.services.subscription import SubscriptionValidator, require_feature

logger = logging.getLogger(__name__)

User = get_user_model()


class TenantRegistrationView(generics.CreateAPIView):
    """
    Endpoint for new tenant self-registration.
    
    Creates a new tenant with:
    - Default "Starter" subscription
    - The registering user as TENANT_ADMIN
    - 14-day free trial
    """
    permission_classes = [AllowAny]
    serializer_class = TenantRegistrationSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        if User.objects.filter(email=data['email']).exists():
            return Response(
                {'error': 'A user with this email already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if Tenant.objects.filter(slug=data['company_slug']).exists():
            return Response(
                {'error': 'This company URL is already taken.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenant = Tenant.objects.create(
            name=data['company_name'],
            slug=data['company_slug'],
            primary_email=data['email'],
            phone=data.get('phone', ''),
            status='ACTIVE'
        )
        
        starter_plan = SubscriptionPlan.objects.filter(name='Starter').first()
        if starter_plan:
            trial_start = timezone.now()
            trial_end_date = trial_start + timezone.timedelta(days=14)
            Subscription.objects.create(
                tenant=tenant,
                plan=starter_plan,
                status='TRIALING',
                trial_start=trial_start,
                trial_end=trial_end_date,
                current_period_start=trial_start,
                current_period_end=trial_end_date
            )
        
        user = User.objects.create_user(
            username=data['email'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', '')
        )
        
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role='TENANT_ADMIN'
        )
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Tenant registration successful',
            'tenant': TenantSerializer(tenant).data,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            'access': str(refresh.access_token),
            'trial_days': 14
        }, status=status.HTTP_201_CREATED)


class TenantDetailView(generics.RetrieveUpdateAPIView):
    """
    Get or update current tenant settings.
    
    Only TENANT_ADMIN can update settings.
    """
    permission_classes = [IsAuthenticated, IsTenantAdmin]
    serializer_class = TenantSerializer
    
    def get_object(self):
        return self.request.tenant


class TenantMembershipViewSet(viewsets.ModelViewSet):
    """
    Manage tenant memberships (users within the tenant).
    
    TENANT_ADMIN can:
    - View all members
    - Add new members
    - Update member roles
    - Remove members (except themselves)
    
    TENANT_STAFF can:
    - View all members
    """
    permission_classes = [IsAuthenticated, CanManageUsers]
    serializer_class = TenantMembershipSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        role = getattr(self.request, 'tenant_role', None)
        
        if role == 'PLATFORM_ADMIN':
            tenant_id = self.request.query_params.get('tenant_id')
            if tenant_id:
                return TenantMembership.objects.filter(tenant_id=tenant_id)
            return TenantMembership.objects.all()
        
        if not tenant:
            return TenantMembership.objects.none()
        
        return TenantMembership.objects.filter(tenant=tenant)
    
    def perform_destroy(self, instance):
        if instance.user == self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot remove yourself from the tenant.")
        instance.delete()


class TenantInvitationViewSet(viewsets.ModelViewSet):
    """
    Manage tenant invitations.
    
    TENANT_ADMIN and TENANT_STAFF can:
    - Create invitations
    - View pending invitations
    - Cancel invitations
    """
    permission_classes = [IsAuthenticated, CanManageUsers]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TenantInvitationCreateSerializer
        return TenantInvitationSerializer
    
    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', None)
        role = getattr(self.request, 'tenant_role', None)
        
        if role == 'PLATFORM_ADMIN':
            return TenantInvitation.objects.all()
        
        if not tenant:
            return TenantInvitation.objects.none()
        
        return TenantInvitation.objects.filter(tenant=tenant)
    
    def perform_create(self, serializer):
        tenant = self.request.tenant
        token = get_random_string(64)
        expires_at = timezone.now() + timezone.timedelta(days=7)
        
        serializer.save(
            tenant=tenant,
            invited_by=self.request.user,
            token=token,
            expires_at=expires_at
        )
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """Resend invitation email."""
        invitation = self.get_object()
        
        if invitation.status != 'PENDING':
            return Response(
                {'error': 'Can only resend pending invitations.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invitation.expires_at = timezone.now() + timezone.timedelta(days=7)
        invitation.save()
        
        return Response({
            'message': 'Invitation resent successfully.',
            'expires_at': invitation.expires_at.isoformat()
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a pending invitation."""
        invitation = self.get_object()
        
        if invitation.status != 'PENDING':
            return Response(
                {'error': 'Can only cancel pending invitations.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invitation.status = 'CANCELLED'
        invitation.save()
        
        return Response({'message': 'Invitation cancelled.'})


@api_view(['GET'])
@permission_classes([AllowAny])
def validate_invitation(request, token):
    """
    Validate an invitation token.
    
    Returns invitation details if valid.
    """
    try:
        invitation = TenantInvitation.objects.get(token=token)
    except TenantInvitation.DoesNotExist:
        return Response(
            {'error': 'Invalid invitation token.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if invitation.status != 'PENDING':
        return Response(
            {'error': 'This invitation is no longer valid.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if invitation.expires_at < timezone.now():
        invitation.status = 'EXPIRED'
        invitation.save()
        return Response(
            {'error': 'This invitation has expired.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return Response({
        'valid': True,
        'email': invitation.email,
        'role': invitation.role,
        'tenant_name': invitation.tenant.name,
        'invited_by': invitation.invited_by.email if invitation.invited_by else None,
        'expires_at': invitation.expires_at.isoformat()
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def accept_invitation(request, token):
    """
    Accept an invitation and create user account.
    
    If user already exists, just adds them to the tenant.
    """
    try:
        invitation = TenantInvitation.objects.get(token=token)
    except TenantInvitation.DoesNotExist:
        return Response(
            {'error': 'Invalid invitation token.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if invitation.status != 'PENDING':
        return Response(
            {'error': 'This invitation is no longer valid.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if invitation.expires_at < timezone.now():
        invitation.status = 'EXPIRED'
        invitation.save()
        return Response(
            {'error': 'This invitation has expired.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = AcceptInvitationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    
    with transaction.atomic():
        user = User.objects.filter(email=invitation.email).first()
        
        if user:
            if TenantMembership.objects.filter(tenant=invitation.tenant, user=user).exists():
                return Response(
                    {'error': 'You are already a member of this tenant.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            user = User.objects.create_user(
                username=invitation.email,
                email=invitation.email,
                password=data['password'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', '')
            )
        
        TenantMembership.objects.create(
            tenant=invitation.tenant,
            user=user,
            role=invitation.role
        )
        
        invitation.status = 'ACCEPTED'
        invitation.accepted_at = timezone.now()
        invitation.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Invitation accepted successfully.',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            'tenant': TenantSerializer(invitation.tenant).data,
            'role': invitation.role,
            'access': str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_tenant_view(request):
    """Get the current user's tenant information."""
    tenant_lazy = getattr(request, 'tenant', None)
    role_lazy = getattr(request, 'tenant_role', None)
    
    try:
        tenant = tenant_lazy.id if tenant_lazy else None
        if tenant:
            tenant = tenant_lazy
    except AttributeError:
        tenant = None
    
    try:
        role = str(role_lazy) if role_lazy and str(role_lazy) else None
    except (AttributeError, TypeError):
        role = None
    
    if not tenant or not hasattr(tenant, 'id'):
        memberships = TenantMembership.objects.filter(user=request.user).select_related('tenant')
        
        if not memberships.exists():
            return Response(
                {'error': 'You are not a member of any tenant.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        tenants = [{
            'id': str(m.tenant.id),
            'name': m.tenant.name,
            'slug': m.tenant.slug,
            'role': m.role
        } for m in memberships]
        
        return Response({
            'current_tenant': None,
            'available_tenants': tenants,
            'message': 'Please select a tenant.'
        })
    
    subscription = Subscription.objects.filter(tenant=tenant).first()
    
    memberships = TenantMembership.objects.filter(user=request.user).select_related('tenant')
    available_tenants = [{
        'id': str(m.tenant.id),
        'name': m.tenant.name,
        'slug': m.tenant.slug,
        'role': m.role,
        'tenant': {
            'id': str(m.tenant.id),
            'name': m.tenant.name,
            'slug': m.tenant.slug,
        }
    } for m in memberships]
    
    return Response({
        'current_tenant': TenantSerializer(tenant).data,
        'current_role': role,
        'available_tenants': available_tenants,
        'subscription': {
            'plan': subscription.plan.name if subscription and subscription.plan else None,
            'status': subscription.status if subscription else None,
            'trial_end': subscription.trial_end.isoformat() if subscription and subscription.trial_end else None
        } if subscription else None
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def subscription_plans_view(request):
    """
    Public endpoint to list available subscription plans.
    Used during tenant onboarding to display pricing options.
    """
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
    
    plans_data = [{
        'id': str(plan.id),
        'name': plan.name,
        'tier': plan.tier,
        'price_monthly': str(plan.price_monthly),
        'price_yearly': str(plan.price_yearly),
        'max_shareholders': plan.max_shareholders,
        'max_transfers_per_month': plan.max_transfers_per_month,
        'max_users': plan.max_users,
    } for plan in plans]
    
    return Response(plans_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def billing_status_view(request):
    """
    Get current billing/subscription status for the tenant.
    """
    from django.conf import settings
    from apps.core.stripe import is_stripe_configured
    
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        return Response(
            {'error': 'No tenant context'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    subscription = Subscription.objects.filter(tenant=tenant).select_related('plan').first()
    
    response_data = {
        'stripe_configured': is_stripe_configured(),
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY if is_stripe_configured() else None,
        'subscription': None,
    }
    
    if subscription:
        response_data['subscription'] = {
            'id': str(subscription.id),
            'status': subscription.status,
            'billing_cycle': subscription.billing_cycle,
            'plan': {
                'id': str(subscription.plan.id),
                'name': subscription.plan.name,
                'tier': subscription.plan.tier,
                'price_monthly': str(subscription.plan.price_monthly),
                'price_yearly': str(subscription.plan.price_yearly),
                'max_shareholders': subscription.plan.max_shareholders,
                'max_transfers_per_month': subscription.plan.max_transfers_per_month,
                'max_users': subscription.plan.max_users,
                'features': subscription.plan.features or [],
            } if subscription.plan else None,
            'trial_end': subscription.trial_end.isoformat() if subscription.trial_end else None,
            'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        }
    
    usage = SubscriptionValidator.get_usage_summary(tenant)
    response_data['usage'] = usage
    
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session_view(request):
    """
    Create a Stripe Checkout session for subscribing to a plan.
    Requires TENANT_ADMIN role.
    """
    from apps.core.services.billing import billing_service
    from apps.core.stripe import is_stripe_configured
    
    if not is_stripe_configured():
        return Response(
            {'error': 'Stripe is not configured'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    tenant = getattr(request, 'tenant', None)
    role = getattr(request, 'tenant_role', None)
    
    if not tenant:
        return Response(
            {'error': 'No tenant context'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if role not in ['PLATFORM_ADMIN', 'TENANT_ADMIN']:
        return Response(
            {'error': 'Only admins can manage billing'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    plan_id = request.data.get('plan_id')
    billing_cycle = request.data.get('billing_cycle', 'monthly')
    
    if not plan_id:
        return Response(
            {'error': 'plan_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
    except SubscriptionPlan.DoesNotExist:
        return Response(
            {'error': 'Invalid plan'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        result = billing_service.create_checkout_session(
            tenant=tenant,
            plan=plan,
            billing_cycle=billing_cycle,
        )
        return Response(result)
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Checkout session failed for tenant {tenant.id}, plan {plan.id}: {str(e)}")
        return Response(
            {'error': f'Failed to create checkout session: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_portal_session_view(request):
    """
    Create a Stripe Billing Portal session for managing subscription.
    Requires TENANT_ADMIN role.
    """
    from apps.core.services.billing import billing_service
    from apps.core.stripe import is_stripe_configured
    
    if not is_stripe_configured():
        return Response(
            {'error': 'Stripe is not configured'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    tenant = getattr(request, 'tenant', None)
    role = getattr(request, 'tenant_role', None)
    
    if not tenant:
        return Response(
            {'error': 'No tenant context'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if role not in ['PLATFORM_ADMIN', 'TENANT_ADMIN']:
        return Response(
            {'error': 'Only admins can manage billing'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not tenant.stripe_customer_id:
        return Response(
            {'error': 'No billing account set up. Subscribe to a plan first.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        result = billing_service.create_billing_portal_session(tenant)
        return Response(result)
    except Exception as e:
        return Response(
            {'error': 'Failed to create portal session'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription_view(request):
    """
    Cancel the tenant's subscription.
    Requires TENANT_ADMIN role.
    """
    from apps.core.services.billing import billing_service
    from apps.core.stripe import is_stripe_configured
    
    if not is_stripe_configured():
        return Response(
            {'error': 'Stripe is not configured'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    tenant = getattr(request, 'tenant', None)
    role = getattr(request, 'tenant_role', None)
    
    if not tenant:
        return Response(
            {'error': 'No tenant context'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if role not in ['PLATFORM_ADMIN', 'TENANT_ADMIN']:
        return Response(
            {'error': 'Only admins can manage billing'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    at_period_end = request.data.get('at_period_end', True)
    
    try:
        result = billing_service.cancel_subscription(tenant, at_period_end=at_period_end)
        return Response(result)
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': 'Failed to cancel subscription'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_manage_role(request):
    """
    Secure endpoint for managing user roles via API.
    Requires ADMIN_SECRET_KEY header for authentication.
    
    Usage:
    POST /api/v1/admin/manage-role/
    Headers: X-Admin-Secret: <your-secret-key>
    Body: {
        "action": "promote" | "create-admin" | "list",
        "email": "user@example.com",
        "tenant_name": "Tenant Name",  # optional for promote if user has only one tenant
        "role": "TENANT_ADMIN",  # for promote action
        "password": "SecurePass123!",  # for create-admin action
        "first_name": "First",  # optional for create-admin
        "last_name": "Last"  # optional for create-admin
    }
    
    IMPORTANT: Remove this endpoint after use for security!
    """
    import os
    
    admin_secret = os.environ.get('ADMIN_SECRET_KEY')
    if not admin_secret:
        return Response(
            {'error': 'ADMIN_SECRET_KEY not configured on server'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    provided_secret = request.headers.get('X-Admin-Secret')
    if not provided_secret or provided_secret != admin_secret:
        return Response(
            {'error': 'Invalid or missing X-Admin-Secret header'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    action = request.data.get('action')
    
    if action == 'list':
        tenant_name = request.data.get('tenant_name')
        
        if tenant_name:
            tenants = Tenant.objects.filter(name__icontains=tenant_name)
            if not tenants.exists():
                return Response({'error': f'Tenant "{tenant_name}" not found'}, status=404)
            memberships = TenantMembership.objects.filter(tenant__in=tenants)
        else:
            memberships = TenantMembership.objects.all()
        
        result = []
        for m in memberships.select_related('user', 'tenant').order_by('tenant__name', 'user__email'):
            result.append({
                'tenant': m.tenant.name,
                'email': m.user.email or '(no email)',
                'role': m.role
            })
        
        return Response({'memberships': result})
    
    elif action == 'promote':
        email = request.data.get('email')
        role = request.data.get('role', 'TENANT_ADMIN')
        tenant_name = request.data.get('tenant_name')
        
        if not email:
            return Response({'error': 'email is required'}, status=400)
        
        if role not in ['PLATFORM_ADMIN', 'TENANT_ADMIN', 'TENANT_STAFF', 'SHAREHOLDER']:
            return Response({'error': f'Invalid role: {role}'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': f'User "{email}" not found'}, status=404)
        
        memberships = TenantMembership.objects.filter(user=user)
        
        if not memberships.exists():
            return Response({'error': f'User "{email}" has no tenant memberships'}, status=404)
        
        if tenant_name:
            tenant = Tenant.objects.filter(name__icontains=tenant_name).first()
            if not tenant:
                return Response({'error': f'Tenant "{tenant_name}" not found'}, status=404)
            membership = memberships.filter(tenant=tenant).first()
            if not membership:
                return Response({'error': f'User is not a member of "{tenant_name}"'}, status=404)
        elif memberships.count() == 1:
            membership = memberships.first()
        else:
            tenants = [m.tenant.name for m in memberships]
            return Response({'error': f'User has multiple tenants. Specify tenant_name. Options: {tenants}'}, status=400)
        
        old_role = membership.role
        membership.role = role
        membership.save()
        
        return Response({
            'success': True,
            'message': f'Changed role for "{email}" in "{membership.tenant.name}": {old_role} -> {role}'
        })
    
    elif action == 'create-admin':
        email = request.data.get('email')
        password = request.data.get('password')
        tenant_name = request.data.get('tenant_name')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        if not all([email, password, tenant_name]):
            return Response({'error': 'email, password, and tenant_name are required'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': f'User "{email}" already exists'}, status=400)
        
        tenant = Tenant.objects.filter(name__icontains=tenant_name).first()
        if not tenant:
            available = list(Tenant.objects.values_list('name', flat=True))
            return Response({'error': f'Tenant "{tenant_name}" not found. Available: {available}'}, status=404)
        
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role='TENANT_ADMIN',
            is_primary_contact=False
        )
        
        return Response({
            'success': True,
            'message': f'Created admin user "{email}" for tenant "{tenant.name}"'
        })
    
    else:
        return Response({
            'error': 'Invalid action. Use: list, promote, or create-admin'
        }, status=400)


# ==============================================================================
# EMAIL API ENDPOINTS
# ==============================================================================

@api_view(['POST'])
@permission_classes([IsPlatformAdmin])
def send_test_email(request):
    """
    Send a test email to verify SES configuration.
    Only available to platform admins.
    
    POST /api/v1/email/test/
    {
        "email": "testadmin@tableicty.com"
    }
    """
    to_email = request.data.get('email')
    
    if not to_email:
        return Response(
            {'error': 'email is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    success = EmailService.send_test_email(to_email)
    
    if success:
        return Response({
            'success': True,
            'message': f'Test email sent to {to_email}'
        })
    else:
        return Response({
            'success': False,
            'error': 'Failed to send test email. Check server logs for details.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsTenantAdmin])
@require_feature('email_invitations')
def send_shareholder_invitation(request):
    """
    Send invitation email to a shareholder.
    Creates JWT token and sends email with registration link.
    Requires Professional or Enterprise tier.
    
    POST /api/v1/email/invite-shareholder/
    {
        "shareholder_id": "uuid",
        "holding_id": "uuid" (optional - for specific holding context),
        "additional_shares": int (optional - for share update notifications, the delta just granted)
    }
    """
    shareholder_id = request.data.get('shareholder_id')
    holding_id = request.data.get('holding_id')
    additional_shares_param = request.data.get('additional_shares')
    
    if not shareholder_id:
        return Response(
            {'error': 'shareholder_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    membership = TenantMembership.objects.filter(user=request.user).first()
    if not membership:
        return Response(
            {'error': 'No tenant membership found'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    tenant = membership.tenant
    
    try:
        shareholder = Shareholder.objects.get(id=shareholder_id, tenant=tenant)
    except Shareholder.DoesNotExist:
        return Response(
            {'error': 'Shareholder not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if not shareholder.email:
        return Response(
            {'error': 'Shareholder has no email address'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    existing_user = User.objects.filter(email=shareholder.email).first()
    
    holding = None
    if holding_id:
        try:
            holding = Holding.objects.get(id=holding_id, shareholder=shareholder)
        except Holding.DoesNotExist:
            pass
    
    if not holding:
        holding = Holding.objects.filter(shareholder=shareholder).first()
    
    from decimal import Decimal, InvalidOperation
    
    if holding:
        issuer = holding.issuer
        company_name = issuer.company_name
        company_id = str(issuer.id)
        share_count = holding.share_quantity
        security_class = holding.security_class
        share_class = f"{security_class.security_type} {security_class.class_designation}"
    else:
        first_issuer = Issuer.objects.filter(tenant=tenant).first()
        company_name = first_issuer.company_name if first_issuer else tenant.name
        company_id = str(first_issuer.id) if first_issuer else str(tenant.id)
        share_count = Decimal('0')
        share_class = ''
    
    if shareholder.entity_name:
        shareholder_name = shareholder.entity_name
    elif shareholder.first_name or shareholder.last_name:
        shareholder_name = f"{shareholder.first_name} {shareholder.last_name}".strip()
    else:
        shareholder_name = 'Shareholder'
    
    all_holdings = Holding.objects.filter(shareholder=shareholder)
    total_shares_decimal = sum(Decimal(str(h.share_quantity)) for h in all_holdings)
    
    if total_shares_decimal <= 0:
        return Response(
            {'error': 'Cannot send email notification: shareholder has no shares'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if existing_user:
        if additional_shares_param is not None:
            try:
                additional_shares_decimal = Decimal(str(additional_shares_param))
            except (InvalidOperation, ValueError, TypeError):
                additional_shares_decimal = Decimal(str(share_count))
        else:
            additional_shares_decimal = Decimal(str(share_count))
        
        try:
            success = EmailService.send_share_update_notification(
                email=shareholder.email,
                shareholder_name=shareholder_name,
                company_name=company_name,
                additional_shares=additional_shares_decimal,
                total_shares=total_shares_decimal,
                share_class=share_class,
                tenant_name=tenant.name,
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Share update notification sent to {shareholder.email}',
                    'shareholder_id': str(shareholder.id),
                    'email_type': 'share_update',
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to send notification email. Check server logs for details.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            import traceback
            error_detail = str(e)
            logger.error(f"Share update email failed for {shareholder.email}: {error_detail}\n{traceback.format_exc()}")
            return Response({
                'success': False,
                'error': f'Email delivery failed: {error_detail}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    share_count_decimal = Decimal(str(share_count))
    share_count_for_display = int(share_count_decimal) if share_count_decimal == share_count_decimal.to_integral_value() else float(share_count_decimal)
    
    token_string, token_hash, expires_at = create_invite_token(
        shareholder_id=str(shareholder.id),
        email=shareholder.email,
        tenant_id=str(tenant.id),
        company_id=company_id,
        company_name=company_name,
        share_count=share_count_for_display,
        share_class=share_class,
    )
    
    TenantInvitation.objects.create(
        tenant=tenant,
        invited_by=request.user,
        email=shareholder.email,
        role='SHAREHOLDER',
        token=token_hash,
        expires_at=expires_at,
        status='PENDING',
    )
    
    try:
        success = EmailService.send_shareholder_invitation(
            email=shareholder.email,
            shareholder_name=shareholder_name,
            company_name=company_name,
            share_count=share_count_for_display,
            share_class=share_class,
            invite_token=token_string,
            tenant_name=tenant.name,
        )
        
        if success:
            return Response({
                'success': True,
                'message': f'Invitation email sent to {shareholder.email}',
                'shareholder_id': str(shareholder.id),
                'expires_at': expires_at.isoformat(),
                'email_type': 'invitation',
            })
        else:
            return Response({
                'success': False,
                'error': 'Failed to send invitation email. Check server logs for details.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        import traceback
        error_detail = str(e)
        logger.error(f"Email sending failed for {shareholder.email}: {error_detail}\n{traceback.format_exc()}")
        return Response({
            'success': False,
            'error': f'Email delivery failed: {error_detail}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_invite_token_view(request):
    """
    Validate an invitation token and return its payload.
    Used by frontend to pre-fill registration form.
    
    POST /api/v1/email/validate-token/
    {
        "token": "jwt-token-string"
    }
    """
    token = request.data.get('token')
    
    if not token:
        return Response(
            {'error': 'token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    is_valid, payload, error = validate_invite_token(token)
    
    if not is_valid:
        return Response({
            'valid': False,
            'error': error or 'Invalid or expired token'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'valid': True,
        'email': payload.get('email'),
        'company_name': payload.get('company_name'),
        'share_count': payload.get('share_count'),
        'share_class': payload.get('share_class'),
        'shareholder_id': payload.get('shareholder_id'),
    })
