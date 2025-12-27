from rest_framework import serializers
from apps.core.models import Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer, AuditLog


class IssuerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issuer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant']


class SecurityClassSerializer(serializers.ModelSerializer):
    issuer_name = serializers.CharField(source='issuer.company_name', read_only=True)
    
    class Meta:
        model = SecurityClass
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant']


class ShareholderSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Shareholder
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant']
        extra_kwargs = {
            'tax_id': {'write_only': True}
        }
    
    def get_full_name(self, obj):
        if obj.account_type == 'ENTITY':
            return obj.entity_name
        return f"{obj.first_name} {obj.last_name}".strip()


class HoldingSerializer(serializers.ModelSerializer):
    shareholder_name = serializers.CharField(source='shareholder.__str__', read_only=True)
    issuer_name = serializers.CharField(source='issuer.company_name', read_only=True)
    security_class_name = serializers.CharField(source='security_class.__str__', read_only=True)
    
    class Meta:
        model = Holding
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant']


class CertificateSerializer(serializers.ModelSerializer):
    issuer_name = serializers.CharField(source='issuer.company_name', read_only=True)
    shareholder_name = serializers.CharField(source='shareholder.__str__', read_only=True)
    
    class Meta:
        model = Certificate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'tenant']


class TransferSerializer(serializers.ModelSerializer):
    issuer_name = serializers.CharField(source='issuer.company_name', read_only=True)
    from_shareholder_name = serializers.CharField(source='from_shareholder.__str__', read_only=True)
    to_shareholder_name = serializers.CharField(source='to_shareholder.__str__', read_only=True)
    
    class Meta:
        model = Transfer
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'processed_by', 'processed_date', 'tenant']


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ['id', 'user', 'user_email', 'action_type', 'model_name', 
                           'object_id', 'object_repr', 'old_value', 'new_value', 
                           'changed_fields', 'timestamp', 'ip_address', 'user_agent', 'request_id']
