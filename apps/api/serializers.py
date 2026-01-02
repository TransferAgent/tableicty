from rest_framework import serializers
from apps.core.models import Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer, AuditLog, CertificateRequest


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
    has_pending_certificate_request = serializers.SerializerMethodField()
    certificate_status = serializers.SerializerMethodField()
    
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
    
    def get_has_pending_certificate_request(self, obj):
        return obj.certificate_requests.filter(status='PENDING').exists()
    
    def get_certificate_status(self, obj):
        if obj.certificate_requests.filter(status='PENDING').exists():
            return 'Certificate'
        return 'Standard'


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


class CertificateRequestSerializer(serializers.ModelSerializer):
    shareholder_name = serializers.SerializerMethodField()
    shareholder_email = serializers.CharField(source='shareholder.email', read_only=True)
    issuer_name = serializers.CharField(source='holding.issuer.company_name', read_only=True)
    security_type = serializers.CharField(source='holding.security_class.class_designation', read_only=True)
    processed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CertificateRequest
        fields = [
            'id',
            'tenant',
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
        read_only_fields = ['id', 'shareholder', 'holding', 'created_at', 'updated_at', 'tenant']
    
    def get_shareholder_name(self, obj):
        if obj.shareholder.account_type == 'INDIVIDUAL':
            return f"{obj.shareholder.first_name} {obj.shareholder.last_name}".strip()
        return obj.shareholder.entity_name or obj.shareholder.email
    
    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}".strip() or obj.processed_by.email
        return None
