"""
Serializers for tenant management.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.core.models import Tenant, TenantMembership, SubscriptionPlan, Subscription, TenantInvitation

User = get_user_model()


class TenantRegistrationSerializer(serializers.Serializer):
    """Serializer for new tenant registration."""
    company_name = serializers.CharField(max_length=255)
    company_slug = serializers.SlugField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    def validate_company_slug(self, value):
        if Tenant.objects.filter(slug=value).exists():
            raise serializers.ValidationError("This company URL is already taken.")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans."""
    id = serializers.CharField(read_only=True)
    
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'slug', 'tier', 'price_monthly', 'price_yearly',
                  'max_shareholders', 'max_transfers_per_month', 'max_users', 'features']
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions."""
    id = serializers.CharField(read_only=True)
    plan = SubscriptionPlanSerializer(read_only=True)
    
    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'status', 'trial_start', 'trial_end',
                  'current_period_start', 'current_period_end', 'cancel_at_period_end']
        read_only_fields = fields


class TenantSerializer(serializers.ModelSerializer):
    """Serializer for tenant details."""
    id = serializers.CharField(read_only=True)
    subscription = serializers.SerializerMethodField()
    
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'primary_email', 'phone', 'website',
                  'address_line1', 'city', 'state', 'zip_code', 'country',
                  'status', 'created_at', 'subscription']
        read_only_fields = ['id', 'slug', 'status', 'created_at']
    
    def get_subscription(self, obj):
        subscription = Subscription.objects.filter(tenant=obj).first()
        if subscription:
            return SubscriptionSerializer(subscription).data
        return None


class UserBriefSerializer(serializers.ModelSerializer):
    """Brief user info for membership displays."""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = fields


class TenantMembershipSerializer(serializers.ModelSerializer):
    """Serializer for tenant memberships."""
    id = serializers.CharField(read_only=True)
    user = UserBriefSerializer(read_only=True)
    user_email = serializers.SerializerMethodField(read_only=True)
    email_input = serializers.EmailField(write_only=True, required=False, source='user_email')
    joined_at = serializers.DateTimeField(source='created_at', read_only=True)
    
    class Meta:
        model = TenantMembership
        fields = ['id', 'user', 'user_email', 'email_input', 'role', 'joined_at']
        read_only_fields = ['id', 'user', 'user_email', 'joined_at']
    
    def get_user_email(self, obj):
        return obj.user.email if obj.user else None
    
    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            return value
        
        requester_role = getattr(request, 'tenant_role', None)
        
        if value == 'PLATFORM_ADMIN' and requester_role != 'PLATFORM_ADMIN':
            raise serializers.ValidationError("Only platform admins can assign PLATFORM_ADMIN role.")
        
        if value == 'TENANT_ADMIN' and requester_role not in ('PLATFORM_ADMIN', 'TENANT_ADMIN'):
            raise serializers.ValidationError("Only tenant admins can assign TENANT_ADMIN role.")
        
        return value


class TenantInvitationSerializer(serializers.ModelSerializer):
    """Serializer for viewing tenant invitations."""
    invited_by = UserBriefSerializer(read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    
    class Meta:
        model = TenantInvitation
        fields = ['id', 'email', 'role', 'status', 'invited_by', 'tenant_name',
                  'created_at', 'expires_at', 'accepted_at']
        read_only_fields = fields


class TenantInvitationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tenant invitations."""
    class Meta:
        model = TenantInvitation
        fields = ['email', 'role']
    
    def validate_email(self, value):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None) if request else None
        
        if tenant:
            if TenantInvitation.objects.filter(
                tenant=tenant, 
                email=value, 
                status='PENDING'
            ).exists():
                raise serializers.ValidationError("An invitation for this email is already pending.")
            
            if TenantMembership.objects.filter(
                tenant=tenant,
                user__email=value
            ).exists():
                raise serializers.ValidationError("This user is already a member of the tenant.")
        
        return value
    
    def validate_role(self, value):
        request = self.context.get('request')
        if not request:
            return value
        
        requester_role = getattr(request, 'tenant_role', None)
        
        if value == 'PLATFORM_ADMIN':
            raise serializers.ValidationError("Cannot invite users as PLATFORM_ADMIN.")
        
        if value == 'TENANT_ADMIN' and requester_role not in ('PLATFORM_ADMIN', 'TENANT_ADMIN'):
            raise serializers.ValidationError("Only tenant admins can invite TENANT_ADMIN users.")
        
        return value


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting an invitation."""
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
