"""
Deal Desk API Serializers.

Provides serializers for term sheet analysis CRUD operations.
"""
from rest_framework import serializers
from apps.deal_desk.models import TermSheetAnalysis, AnalysisRedFlag, AnalysisScenario


class AnalysisRedFlagSerializer(serializers.ModelSerializer):
    """Serializer for red flags identified in term sheet."""
    
    class Meta:
        model = AnalysisRedFlag
        fields = [
            'id',
            'flag_type',
            'severity',
            'title',
            'description',
            'prevalence',
            'recommendation',
        ]
        read_only_fields = ['id']


class AnalysisScenarioSerializer(serializers.ModelSerializer):
    """Serializer for alternative negotiation scenarios."""
    
    class Meta:
        model = AnalysisScenario
        fields = [
            'id',
            'scenario_label',
            'title',
            'description',
            'new_valuation',
            'new_dilution_pct',
            'likelihood_of_acceptance',
        ]
        read_only_fields = ['id']


class TermSheetAnalysisListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list view.
    Shows key metrics without full nested data.
    """
    red_flags_count = serializers.SerializerMethodField()
    scenarios_count = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = TermSheetAnalysis
        fields = [
            'id',
            'file_name',
            'status',
            'status_display',
            'pre_money_valuation',
            'investment_amount',
            'post_money_valuation',
            'dilution_pct',
            'red_flags_count',
            'scenarios_count',
            'created_at',
            'completed_at',
        ]
        read_only_fields = fields
    
    def get_red_flags_count(self, obj):
        return obj.red_flags.count()
    
    def get_scenarios_count(self, obj):
        return obj.scenarios.count()


class TermSheetAnalysisDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer with all details and nested relationships.
    Used for single analysis retrieval.
    """
    red_flags = AnalysisRedFlagSerializer(many=True, read_only=True)
    scenarios = AnalysisScenarioSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    deal_summary = serializers.SerializerMethodField()
    dilution_analysis = serializers.SerializerMethodField()
    key_terms = serializers.SerializerMethodField()
    
    class Meta:
        model = TermSheetAnalysis
        fields = [
            'id',
            'file_name',
            'file_size_bytes',
            'user_notes',
            'status',
            'status_display',
            'error_message',
            'deal_summary',
            'dilution_analysis',
            'key_terms',
            'plain_english_explanation',
            'ai_confidence_score',
            'red_flags',
            'scenarios',
            'created_at',
            'started_at',
            'completed_at',
            'processing_time_seconds',
        ]
        read_only_fields = fields
    
    def get_deal_summary(self, obj):
        """Return structured deal summary."""
        return {
            'pre_money_valuation': str(obj.pre_money_valuation) if obj.pre_money_valuation else None,
            'investment_amount': str(obj.investment_amount) if obj.investment_amount else None,
            'post_money_valuation': str(obj.post_money_valuation) if obj.post_money_valuation else None,
            'new_shares_issued': obj.new_shares_issued,
            'price_per_share': str(obj.price_per_share) if obj.price_per_share else None,
            'option_pool_increase_pct': str(obj.option_pool_increase_pct) if obj.option_pool_increase_pct else None,
        }
    
    def get_dilution_analysis(self, obj):
        """Return structured dilution analysis."""
        return {
            'founder_shares_before': obj.founder_shares_before,
            'total_shares_before': obj.total_shares_before,
            'founder_ownership_before_pct': str(obj.founder_ownership_before_pct) if obj.founder_ownership_before_pct else None,
            'founder_shares_after': obj.founder_shares_after,
            'total_shares_after': obj.total_shares_after,
            'founder_ownership_after_pct': str(obj.founder_ownership_after_pct) if obj.founder_ownership_after_pct else None,
            'dilution_pct': str(obj.dilution_pct) if obj.dilution_pct else None,
        }
    
    def get_key_terms(self, obj):
        """Return structured key legal terms."""
        return {
            'liquidation_preference_multiple': str(obj.liquidation_preference_multiple) if obj.liquidation_preference_multiple else None,
            'liquidation_preference_type': obj.liquidation_preference_type,
            'anti_dilution_type': obj.anti_dilution_type,
            'board_composition': obj.board_composition,
        }


class TermSheetAnalysisCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new analysis (file upload).
    Validates PDF file and initiates async processing.
    """
    term_sheet_file = serializers.FileField(required=True, write_only=True)
    user_notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = TermSheetAnalysis
        fields = ['term_sheet_file', 'user_notes']
    
    def validate_term_sheet_file(self, value):
        """Validate uploaded file is PDF and under size limit."""
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are supported.")
        
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must be less than 10MB.")
        
        return value
    
    def create(self, validated_data):
        """Create analysis record with file metadata."""
        request = self.context.get('request')
        tenant = self.context.get('tenant')
        
        if not tenant:
            raise serializers.ValidationError("Tenant context is required.")
        
        term_sheet_file = validated_data['term_sheet_file']
        
        analysis = TermSheetAnalysis.objects.create(
            tenant=tenant,
            created_by=request.user,
            term_sheet_file=term_sheet_file,
            file_name=term_sheet_file.name,
            file_size_bytes=term_sheet_file.size,
            user_notes=validated_data.get('user_notes', ''),
            status='PENDING',
        )
        
        return analysis
