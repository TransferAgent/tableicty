from django.contrib import admin
from .models import TermSheetAnalysis, AnalysisRedFlag, AnalysisScenario


class AnalysisRedFlagInline(admin.TabularInline):
    model = AnalysisRedFlag
    extra = 0
    readonly_fields = ['id', 'created_at']


class AnalysisScenarioInline(admin.TabularInline):
    model = AnalysisScenario
    extra = 0
    readonly_fields = ['id', 'created_at']


@admin.register(TermSheetAnalysis)
class TermSheetAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'file_name',
        'tenant',
        'created_by',
        'status',
        'investment_amount',
        'dilution_pct',
        'red_flags_count',
        'created_at',
    ]
    list_filter = ['status', 'tenant', 'created_at']
    search_fields = ['file_name', 'tenant__name', 'created_by__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at']
    
    fieldsets = (
        ('File Info', {
            'fields': ('id', 'tenant', 'created_by', 'term_sheet_file', 'file_name', 'file_size_bytes', 'user_notes')
        }),
        ('Financial Terms', {
            'fields': (
                'pre_money_valuation',
                'investment_amount',
                'post_money_valuation',
                'new_shares_issued',
                'price_per_share',
                'option_pool_increase_pct',
            )
        }),
        ('Legal Terms', {
            'fields': (
                'liquidation_preference_multiple',
                'liquidation_preference_type',
                'anti_dilution_type',
                'board_composition',
            )
        }),
        ('Dilution Analysis', {
            'fields': (
                'founder_shares_before',
                'total_shares_before',
                'founder_ownership_before_pct',
                'founder_shares_after',
                'total_shares_after',
                'founder_ownership_after_pct',
                'dilution_pct',
            )
        }),
        ('AI Analysis', {
            'fields': (
                'plain_english_explanation',
                'ai_confidence_score',
                'ai_full_response',
            )
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'created_at', 'updated_at', 'completed_at')
        }),
    )
    
    inlines = [AnalysisRedFlagInline, AnalysisScenarioInline]


@admin.register(AnalysisRedFlag)
class AnalysisRedFlagAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'analysis', 'created_at']
    list_filter = ['severity', 'flag_type']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at']


@admin.register(AnalysisScenario)
class AnalysisScenarioAdmin(admin.ModelAdmin):
    list_display = ['scenario_label', 'title', 'analysis', 'likelihood_of_acceptance']
    list_filter = ['likelihood_of_acceptance']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at']
