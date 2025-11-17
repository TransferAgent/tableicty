from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.core.models import Shareholder


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
            'is_accredited_investor',
            'email_alerts_enabled',
            'paper_statements_enabled',
        ]
        read_only_fields = [
            'id',
            'email',
            'account_type',
            'first_name',
            'middle_name',
            'last_name',
            'entity_name',
            'tax_id_masked',
            'tax_id_type',
            'is_accredited_investor',
        ]
    
    def get_tax_id_masked(self, obj):
        if obj.tax_id:
            tax_id_str = str(obj.tax_id)
            if len(tax_id_str) >= 4:
                return f"***-**-{tax_id_str[-4:]}"
        return "***-**-****"
    
    def update(self, instance, validated_data):
        # Only allow updating specific fields
        allowed_fields = ['address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country', 'phone', 'email_alerts_enabled', 'paper_statements_enabled']
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
