from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.core.models import Shareholder, Transfer, Certificate, AuditLog
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

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def validate_invite_token(self, value):
        # Validate invite token exists in database (mock for now)
        # In production, check a RegistrationToken model
        if not value:
            raise serializers.ValidationError("Invalid invite token")
        return value
    
    def create(self, validated_data):
        invite_token = validated_data.pop('invite_token')
        validated_data.pop('password_confirm')
        
        # TODO: Look up Shareholder by invite_token
        # For now, find shareholder by email
        try:
            shareholder = Shareholder.objects.get(email=validated_data['email'], user__isnull=True)
        except Shareholder.DoesNotExist:
            raise serializers.ValidationError(
                "No shareholder account found for this email. Please contact support."
            )
        
        # Create user
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=shareholder.first_name or '',
            last_name=shareholder.last_name or ''
        )
        
        # Link user to shareholder
        shareholder.user = user
        shareholder.save()
        
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
    certificate_number = serializers.CharField(required=True)
    issuer_id = serializers.UUIDField(required=True)
    conversion_type = serializers.ChoiceField(
        choices=[
            ('CERT_TO_DRS', 'Convert Physical Certificate to DRS'),
            ('DRS_TO_CERT', 'Convert DRS to Physical Certificate'),
        ],
        required=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        request = self.context.get('request')
        shareholder = request.user.shareholder
        
        if attrs['conversion_type'] == 'CERT_TO_DRS':
            try:
                cert = Certificate.objects.get(
                    certificate_number=attrs['certificate_number'],
                    issuer_id=attrs['issuer_id'],
                    shareholder=shareholder,
                    status='OUTSTANDING'
                )
                attrs['certificate'] = cert
            except Certificate.DoesNotExist:
                raise serializers.ValidationError(
                    "Certificate not found or not eligible for conversion"
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
