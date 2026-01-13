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
        try:
            return obj.certificate_requests.filter(status='PENDING').exists()
        except Exception:
            return False
    
    def get_certificate_status(self, obj):
        try:
            if obj.certificate_requests.filter(status='PENDING').exists():
                return 'PENDING'
            if obj.certificate_requests.filter(status='PROCESSING').exists():
                return 'PROCESSING'
            if obj.certificate_requests.filter(status='COMPLETED').exists():
                return 'COMPLETED'
            if obj.certificate_requests.filter(status='REJECTED').exists():
                return 'REJECTED'
        except Exception:
            pass
        return None


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


class CertificateRequestShareholderSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Shareholder
        fields = ['id', 'first_name', 'last_name', 'email', 'full_name']
    
    def get_full_name(self, obj):
        if obj.account_type == 'INDIVIDUAL':
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.entity_name or obj.email


class CertificateRequestHoldingSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    issuer = serializers.SerializerMethodField()
    security_class = serializers.SerializerMethodField()
    share_quantity = serializers.DecimalField(max_digits=20, decimal_places=4)
    
    def get_issuer(self, obj):
        try:
            # Correct relationship chain:
            # Holding → Shareholder → Tenant (issuer)
            if obj and obj.shareholder and obj.shareholder.tenant:
                return {
                    'id': str(obj.shareholder.tenant.id),
                    'company_name': obj.shareholder.tenant.name
                }
        except AttributeError:
            pass
        return None
    
    def get_security_class(self, obj):
        try:
            if obj and obj.security_class:
                return {
                    'id': str(obj.security_class.id),
                    'name': obj.security_class.name or obj.security_class.class_designation
                }
        except AttributeError:
            pass
        return None


class CertificateRequestSerializer(serializers.ModelSerializer):
    shareholder = serializers.SerializerMethodField()
    holding = serializers.SerializerMethodField()
    shareholder_name = serializers.SerializerMethodField()
    shareholder_email = serializers.SerializerMethodField()
    issuer_name = serializers.SerializerMethodField()
    security_type = serializers.SerializerMethodField()
    processed_by_name = serializers.SerializerMethodField()
    shareholder_notes = serializers.CharField(required=False, allow_blank=True, read_only=True)
    
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
            'shareholder_notes',
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
    
    def get_shareholder(self, obj):
        if obj.shareholder:
            return CertificateRequestShareholderSerializer(obj.shareholder).data
        return None
    
    def get_holding(self, obj):
        if obj.holding:
            return CertificateRequestHoldingSerializer(obj.holding).data
        return None
    
    def get_shareholder_name(self, obj):
        if not obj.shareholder:
            return 'Unknown Shareholder'
        if obj.shareholder.account_type == 'INDIVIDUAL':
            return f"{obj.shareholder.first_name} {obj.shareholder.last_name}".strip()
        return obj.shareholder.entity_name or obj.shareholder.email
    
    def get_shareholder_email(self, obj):
        if obj.shareholder:
            return obj.shareholder.email
        return None
    
    def get_issuer_name(self, obj):
        try:
            # Correct relationship: Holding → Shareholder → Tenant (issuer)
            if obj.holding and obj.holding.shareholder and obj.holding.shareholder.tenant:
                return obj.holding.shareholder.tenant.name
        except AttributeError:
            pass
        return None
    
    def get_security_type(self, obj):
        if obj.holding and obj.holding.security_class:
            return obj.holding.security_class.class_designation
        return None
    
    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.first_name} {obj.processed_by.last_name}".strip() or obj.processed_by.email
        return None
