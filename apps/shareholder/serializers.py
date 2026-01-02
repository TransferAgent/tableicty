from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.core.models import Shareholder, Transfer, Certificate, AuditLog, Holding, TenantMembership, TenantInvitation, CertificateRequest
from apps.core.services.invite_tokens import validate_invite_token
from decimal import Decimal


class ShareholderRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    invite_token = serializers.CharField(required=True, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def validate_invite_token(self, value):
        if not value:
            raise serializers.ValidationError("Invite token is required")
        
        is_valid, payload, error = validate_invite_token(value)
        
        if not is_valid:
            raise serializers.ValidationError(f"Invalid or expired invite token: {error}")
        
        self._token_payload = payload
        return value
    
    def create(self, validated_data):
        validated_data.pop('invite_token')
        validated_data.pop('password_confirm')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        
        payload = getattr(self, '_token_payload', {})
        shareholder_id = payload.get('shareholder_id')
        tenant_id = payload.get('tenant_id')
        email_from_token = payload.get('email')
        
        if email_from_token and email_from_token.lower() != validated_data['email'].lower():
            raise serializers.ValidationError({
                "email": "Email does not match the invitation"
            })
        
        shareholder = None
        if shareholder_id:
            try:
                shareholder = Shareholder.objects.get(id=shareholder_id, user__isnull=True)
            except Shareholder.DoesNotExist:
                pass
        
        if not shareholder:
            try:
                shareholder = Shareholder.objects.get(email=validated_data['email'], user__isnull=True)
            except Shareholder.DoesNotExist:
                raise serializers.ValidationError(
                    "No shareholder account found for this email. Please contact support."
                )
        
        user_first_name = first_name or shareholder.first_name or ''
        user_last_name = last_name or shareholder.last_name or ''
        
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=user_first_name,
            last_name=user_last_name
        )
        
        shareholder.user = user
        shareholder.save()
        
        if shareholder.tenant:
            existing = TenantMembership.objects.filter(user=user, tenant=shareholder.tenant).first()
            if not existing:
                TenantMembership.objects.create(
                    tenant=shareholder.tenant,
                    user=user,
                    role='SHAREHOLDER',
                    is_primary_contact=False
                )
        
        token_hash = payload.get('token_hash')
        if token_hash:
            TenantInvitation.objects.filter(
                token=token_hash,
                status='PENDING'
            ).update(
                status='ACCEPTED',
                accepted_at=timezone.now(),
                accepted_by=user
            )
        
        return user


class ShareholderProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    tax_id_masked = serializers.SerializerMethodField()
    
    class Meta:
        model = Shareholder
        fields = [
            'id',
            'email',
            'account_type',
            'first_name',
            'middle_name',
            'last_name',
            'entity_name',
            'tax_id_masked',
            'tax_id_type',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'zip_code',
            'country',
            'phone',
            'accredited_investor',
            'email_notifications',
            'paper_statements',
        ]
        read_only_fields = [
            'id',
            'email',
            'account_type',
            'entity_name',
            'tax_id_masked',
            'tax_id_type',
            'accredited_investor',
        ]
        extra_kwargs = {
            'first_name': {'allow_blank': False, 'required': False},
            'last_name': {'allow_blank': False, 'required': False},
        }
    
    def get_tax_id_masked(self, obj):
        if obj.tax_id:
            tax_id_str = str(obj.tax_id)
            if len(tax_id_str) >= 4:
                return f"***-**-{tax_id_str[-4:]}"
        return "***-**-****"
    
    def validate_first_name(self, value):
        """Ensure first_name is not blank for INDIVIDUAL accounts"""
        account_type = self.instance.account_type if self.instance else self.initial_data.get('account_type')
        
        if account_type == 'INDIVIDUAL' and not value:
            raise serializers.ValidationError("First name is required for individual accounts.")
        return value
    
    def validate_last_name(self, value):
        """Ensure last_name is not blank for INDIVIDUAL accounts"""
        account_type = self.instance.account_type if self.instance else self.initial_data.get('account_type')
        
        if account_type == 'INDIVIDUAL' and not value:
            raise serializers.ValidationError("Last name is required for individual accounts.")
        return value
    
    def validate_entity_name(self, value):
        """Ensure entity_name is not blank for ENTITY/JOINT accounts"""
        account_type = self.instance.account_type if self.instance else self.initial_data.get('account_type')
        
        if account_type in ['ENTITY', 'JOINT'] and not value:
            raise serializers.ValidationError("Entity name is required for entity/joint accounts.")
        return value
    
    def update(self, instance, validated_data):
        # Only allow updating specific fields
        allowed_fields = ['first_name', 'middle_name', 'last_name', 'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country', 'phone', 'email_notifications', 'paper_statements']
        for field in allowed_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance


class UserSerializer(serializers.ModelSerializer):
    shareholder = ShareholderProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'shareholder']
        read_only_fields = ['id', 'username']


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs


class TransferSerializer(serializers.ModelSerializer):
    issuer_name = serializers.CharField(source='issuer.company_name', read_only=True)
    issuer_ticker = serializers.CharField(source='issuer.ticker_symbol', read_only=True)
    security_type = serializers.CharField(source='security_class.security_type', read_only=True)
    security_designation = serializers.CharField(source='security_class.class_designation', read_only=True)
    from_shareholder_name = serializers.SerializerMethodField()
    to_shareholder_name = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    
    class Meta:
        model = Transfer
        fields = [
            'id',
            'issuer_name',
            'issuer_ticker',
            'security_type',
            'security_designation',
            'from_shareholder_name',
            'to_shareholder_name',
            'share_quantity',
            'transfer_price',
            'transfer_date',
            'transfer_type',
            'status',
            'direction',
            'notes',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_from_shareholder_name(self, obj):
        if obj.from_shareholder.account_type == 'ENTITY':
            return obj.from_shareholder.entity_name
        return f"{obj.from_shareholder.first_name} {obj.from_shareholder.last_name}".strip()
    
    def get_to_shareholder_name(self, obj):
        if obj.to_shareholder.account_type == 'ENTITY':
            return obj.to_shareholder.entity_name
        return f"{obj.to_shareholder.first_name} {obj.to_shareholder.last_name}".strip()
    
    def get_direction(self, obj):
        request = self.context.get('request')
        if request and hasattr(request.user, 'shareholder'):
            shareholder = request.user.shareholder
            if obj.from_shareholder == shareholder:
                return 'OUT'
            elif obj.to_shareholder == shareholder:
                return 'IN'
        return None


class TaxDocumentSerializer(serializers.Serializer):
    id = serializers.CharField()
    document_type = serializers.CharField()
    tax_year = serializers.IntegerField()
    issuer_name = serializers.CharField()
    issuer_ticker = serializers.CharField()
    generated_date = serializers.DateField()
    status = serializers.CharField()
    download_url = serializers.CharField()


class CertificateConversionRequestSerializer(serializers.Serializer):
    holding_id = serializers.UUIDField(required=True)
    conversion_type = serializers.ChoiceField(
        choices=[
            ('CERT_TO_DRS', 'Convert Physical Certificate to DRS'),
            ('DRS_TO_CERT', 'Convert DRS to Physical Certificate'),
        ],
        required=True
    )
    share_quantity = serializers.IntegerField(required=True, min_value=1)
    mailing_address = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        request = self.context.get('request')
        shareholder = request.user.shareholder
        
        try:
            holding = Holding.objects.get(
                id=attrs['holding_id'],
                shareholder=shareholder
            )
            attrs['holding'] = holding
        except Holding.DoesNotExist:
            raise serializers.ValidationError(
                "Holding not found or does not belong to this shareholder"
            )
        
        if attrs['share_quantity'] > holding.share_quantity:
            raise serializers.ValidationError(
                f"Cannot convert more than {int(holding.share_quantity)} shares"
            )
        
        if attrs['conversion_type'] == 'DRS_TO_CERT' and not attrs.get('mailing_address'):
            raise serializers.ValidationError(
                "Mailing address is required for physical certificate requests"
            )
        
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Update shareholder profile.
    
    NOTE: DRF partial=True filters empty strings from validated_data,
    preventing users from blanking required fields.
    """
    class Meta:
        model = Shareholder
        fields = [
            'first_name',
            'middle_name',
            'last_name',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'zip_code',
            'country',
            'phone',
            'email_notifications',
            'paper_statements',
        ]
        extra_kwargs = {
            'first_name': {'allow_blank': False, 'required': False},
            'last_name': {'allow_blank': False, 'required': False},
        }
    
    def validate_first_name(self, value):
        """Ensure first_name is not blank for INDIVIDUAL accounts"""
        if self.instance and self.instance.account_type == 'INDIVIDUAL' and not value:
            raise serializers.ValidationError("First name is required for individual accounts.")
        return value
    
    def validate_last_name(self, value):
        """Ensure last_name is not blank for INDIVIDUAL accounts"""
        if self.instance and self.instance.account_type == 'INDIVIDUAL' and not value:
            raise serializers.ValidationError("Last name is required for individual accounts.")
        return value
    
    def validate(self, attrs):
        """Validate required fields based on account type"""
        instance = self.instance
        if not instance:
            return attrs
        
        # For INDIVIDUAL accounts, ensure names are not blank
        if instance.account_type == 'INDIVIDUAL':
            # Check first_name - either from attrs or existing instance
            first_name = attrs.get('first_name', instance.first_name)
            if 'first_name' in attrs and not attrs['first_name']:
                raise serializers.ValidationError({
                    'first_name': "First name is required for individual accounts."
                })
            
            # Check last_name - either from attrs or existing instance
            last_name = attrs.get('last_name', instance.last_name)
            if 'last_name' in attrs and not attrs['last_name']:
                raise serializers.ValidationError({
                    'last_name': "Last name is required for individual accounts."
                })
        
        return attrs
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        changed_fields = []
        
        # Prevent blanking out required fields for INDIVIDUAL accounts
        if instance.account_type == 'INDIVIDUAL':
            if 'first_name' in validated_data and not validated_data['first_name']:
                raise serializers.ValidationError({
                    'first_name': "First name is required for individual accounts."
                })
            if 'last_name' in validated_data and not validated_data['last_name']:
                raise serializers.ValidationError({
                    'last_name': "Last name is required for individual accounts."
                })
        
        for field, value in validated_data.items():
            old_value = getattr(instance, field)
            if old_value != value:
                changed_fields.append({
                    'field': field,
                    'old_value': str(old_value) if old_value is not None else '',
                    'new_value': str(value) if value is not None else ''
                })
                setattr(instance, field, value)
        
        instance.save()
        
        if changed_fields and request:
            from apps.core.signals import set_audit_signal_flag, clear_audit_signal_flag
            set_audit_signal_flag()
            try:
                AuditLog.objects.create(
                    model_name='SHAREHOLDER',
                    object_id=str(instance.id),
                    action_type='UPDATE',
                    user=request.user,
                    user_email=request.user.email,
                    object_repr=f"{instance.first_name} {instance.last_name}".strip() or instance.email,
                    old_value=changed_fields[0]['old_value'] if changed_fields else None,
                    new_value={field['field']: field['new_value'] for field in changed_fields},
                    changed_fields=[field['field'] for field in changed_fields],
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
                )
            finally:
                clear_audit_signal_flag()
        
        return instance


class CertificateRequestSerializer(serializers.ModelSerializer):
    """Serializer for shareholder viewing their certificate requests"""
    issuer_name = serializers.CharField(source='holding.issuer.company_name', read_only=True)
    security_type = serializers.CharField(source='holding.security_class.class_designation', read_only=True)
    
    class Meta:
        model = CertificateRequest
        fields = [
            'id',
            'conversion_type',
            'share_quantity',
            'mailing_address',
            'status',
            'issuer_name',
            'security_type',
            'created_at',
            'processed_at',
            'rejection_reason',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'processed_at', 'rejection_reason']


class CertificateRequestAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin viewing/processing certificate requests"""
    shareholder_name = serializers.SerializerMethodField()
    shareholder_email = serializers.CharField(source='shareholder.email', read_only=True)
    issuer_name = serializers.CharField(source='holding.issuer.company_name', read_only=True)
    security_type = serializers.CharField(source='holding.security_class.class_designation', read_only=True)
    processed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CertificateRequest
        fields = [
            'id',
            'shareholder',
            'shareholder_name',
            'shareholder_email',
            'holding',
            'issuer_name',
            'security_type',
            'conversion_type',
            'share_quantity',
            'mailing_address',
            'status',
            'rejection_reason',
            'admin_notes',
            'processed_by',
            'processed_by_name',
            'processed_at',
            'certificate_number',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'shareholder', 'holding', 'created_at', 'updated_at']
    
    def get_shareholder_name(self, obj):
        if obj.shareholder.account_type == 'INDIVIDUAL':
            return f"{obj.shareholder.first_name} {obj.shareholder.last_name}".strip()
        return obj.shareholder.entity_name or obj.shareholder.email
    
    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}".strip() or obj.processed_by.email
        return None
