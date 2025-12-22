"""
Tenant management API views.

Provides endpoints for:
- Tenant self-registration (onboarding)
- Tenant settings management
- User invitation workflow
"""
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
    Tenant, TenantMembership, SubscriptionPlan, Subscription, TenantInvitation
)
from apps.core.permissions import IsTenantAdmin, CanManageUsers, IsPlatformAdmin
from apps.core.serializers import (
    TenantRegistrationSerializer, TenantSerializer, TenantMembershipSerializer,
    TenantInvitationSerializer, TenantInvitationCreateSerializer,
    AcceptInvitationSerializer
)

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
    
    return Response({
        'tenant': TenantSerializer(tenant).data,
        'role': role,
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
            } if subscription.plan else None,
            'trial_end': subscription.trial_end.isoformat() if subscription.trial_end else None,
            'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        }
    
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
        return Response(
            {'error': 'Failed to create checkout session'},
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
