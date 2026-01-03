# DEAL DESK - APP BUILDER SPRINT SPECIFICATION
## Technical Implementation Guide

**Version:** 1.0  
**Date:** January 3, 2026  
**Sprint Duration:** 2 weeks  
**Build Approach:** Incremental (testable milestones every 2-3 days)  
**Reference Doc:** Prime_Directive_Deal_Desk_v2.md

---

## 🎯 OVERVIEW

### What We're Building
An AI-powered term sheet analyzer that helps founders understand dilution, identify red flags, and generate negotiation scenarios.

### Key Components
1. **Backend:** Django models, API endpoints, OpenAI integration
2. **Frontend:** React upload UI, analysis dashboard, detailed report
3. **AI Engine:** GPT-4 Turbo prompt for term sheet analysis
4. **Billing:** Stripe usage limits (freemium enforcement)

### Success Criteria
- Founder uploads PDF → AI analyzes → Report ready in 60 seconds
- Multi-tenant isolation (each tenant sees only their analyses)
- Usage limits enforced (Free: 1, Starter: 3/year, Pro: unlimited)
- AI confidence score >85% on average

---

## 📦 PHASE 1: BACKEND FOUNDATION (Days 1-4)

### Sprint 1A: Data Models (Day 1)

**File:** `apps/core/models.py`

**Task 1.1: Create TermSheetAnalysis Model**

```python
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class TermSheetAnalysis(models.Model):
    """
    Main model for term sheet analysis.
    Stores uploaded PDF, extracted data, and AI-generated analysis.
    """
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Multi-tenant relationships
    tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.CASCADE,
        related_name='term_sheet_analyses',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_analyses'
    )
    
    # File upload
    term_sheet_file = models.FileField(
        upload_to='term_sheets/%Y/%m/',
        help_text="PDF file of the term sheet"
    )
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.IntegerField()
    
    # Optional notes from user
    user_notes = models.TextField(
        null=True,
        blank=True,
        help_text="Optional context from the founder"
    )
    
    # Extracted financial terms
    pre_money_valuation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    investment_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    post_money_valuation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    new_shares_issued = models.BigIntegerField(null=True, blank=True)
    price_per_share = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )
    option_pool_increase_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Key legal terms
    liquidation_preference_multiple = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="e.g., 1.0, 1.5, 2.0"
    )
    liquidation_preference_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="participating, non-participating, or capped"
    )
    anti_dilution_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="full_ratchet, weighted_average, broad_based, or none"
    )
    board_composition = models.JSONField(
        null=True,
        blank=True,
        help_text="e.g., {'founder': 2, 'investor': 3, 'independent': 1}"
    )
    
    # Dilution analysis (calculated from cap table + new investment)
    founder_shares_before = models.BigIntegerField(null=True, blank=True)
    total_shares_before = models.BigIntegerField(null=True, blank=True)
    founder_ownership_before_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    founder_shares_after = models.BigIntegerField(null=True, blank=True)
    total_shares_after = models.BigIntegerField(null=True, blank=True)
    founder_ownership_after_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    dilution_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Negative number represents ownership decrease"
    )
    
    # AI-generated content
    ai_full_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Complete JSON response from OpenAI"
    )
    plain_english_explanation = models.TextField(
        null=True,
        blank=True,
        help_text="Plain English summary of the deal"
    )
    ai_confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text="0.0-1.0, confidence in extraction accuracy"
    )
    
    # Processing status
    STATUS_CHOICES = [
        ('UPLOADED', 'Uploaded'),
        ('EXTRACTING', 'Extracting Text'),
        ('ANALYZING', 'Analyzing with AI'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UPLOADED',
        db_index=True
    )
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'core_termsheetanalysis'
        ordering = ['-created_at']
        verbose_name = 'Term Sheet Analysis'
        verbose_name_plural = 'Term Sheet Analyses'
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['created_by', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.file_name} - {self.status} ({self.tenant.name})"
    
    @property
    def red_flags_count(self):
        """Count of detected red flags."""
        return self.red_flags.count()
    
    @property
    def scenarios_count(self):
        """Count of alternative scenarios."""
        return self.scenarios.count()


class AnalysisRedFlag(models.Model):
    """
    Individual red flags detected in the term sheet.
    Linked to parent TermSheetAnalysis.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        TermSheetAnalysis,
        on_delete=models.CASCADE,
        related_name='red_flags'
    )
    
    # Red flag details
    flag_type = models.CharField(
        max_length=100,
        help_text="e.g., 'full_ratchet_anti_dilution', 'participating_preferred'"
    )
    
    SEVERITY_CHOICES = [
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('CRITICAL', 'Critical Risk'),
    ]
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    
    title = models.CharField(
        max_length=255,
        help_text="e.g., 'Full Ratchet Anti-Dilution Detected'"
    )
    description = models.TextField(
        help_text="Plain English explanation of the risk"
    )
    prevalence = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="e.g., 'Only 5% of seed deals include this'"
    )
    recommendation = models.TextField(
        help_text="Actionable advice on how to address this"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_analysisredflag'
        ordering = ['-severity', 'created_at']
        verbose_name = 'Analysis Red Flag'
        verbose_name_plural = 'Analysis Red Flags'
    
    def __str__(self):
        return f"{self.severity}: {self.title}"


class AnalysisScenario(models.Model):
    """
    Alternative negotiation scenarios generated by AI.
    Linked to parent TermSheetAnalysis.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        TermSheetAnalysis,
        on_delete=models.CASCADE,
        related_name='scenarios'
    )
    
    # Scenario details
    scenario_label = models.CharField(
        max_length=50,
        help_text="e.g., 'Scenario A', 'Scenario B'"
    )
    title = models.CharField(
        max_length=255,
        help_text="e.g., 'Counter with Standard Terms'"
    )
    description = models.TextField(
        help_text="Detailed explanation of proposed changes"
    )
    
    # Impact estimates
    new_valuation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    new_dilution_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    likelihood_of_acceptance = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="'High', 'Medium', or 'Low'"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'core_analysisscenario'
        ordering = ['scenario_label']
        verbose_name = 'Analysis Scenario'
        verbose_name_plural = 'Analysis Scenarios'
    
    def __str__(self):
        return f"{self.scenario_label}: {self.title}"
```

**Task 1.2: Create Django Migration**

```bash
# After adding models to apps/core/models.py
python manage.py makemigrations core --name add_deal_desk_models
python manage.py migrate
```

**Task 1.3: Register in Django Admin**

```python
# apps/core/admin.py

from django.contrib import admin
from .models import TermSheetAnalysis, AnalysisRedFlag, AnalysisScenario


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
    readonly_fields = ['created_at', 'updated_at', 'completed_at']
    
    fieldsets = (
        ('File Info', {
            'fields': ('term_sheet_file', 'file_name', 'file_size_bytes', 'user_notes')
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


@admin.register(AnalysisRedFlag)
class AnalysisRedFlagAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'analysis', 'created_at']
    list_filter = ['severity', 'flag_type']
    search_fields = ['title', 'description']


@admin.register(AnalysisScenario)
class AnalysisScenarioAdmin(admin.ModelAdmin):
    list_display = ['scenario_label', 'title', 'analysis', 'likelihood_of_acceptance']
    list_filter = ['likelihood_of_acceptance']
    search_fields = ['title', 'description']
```

**Testing Checklist (Day 1):**
- [ ] Models created without errors
- [ ] Migrations applied successfully
- [ ] Django admin shows all three models
- [ ] Can create test records via admin interface

---

### Sprint 1B: API Endpoints (Days 2-3)

**File:** `apps/api/serializers.py`

**Task 1.4: Create Serializers**

```python
from rest_framework import serializers
from apps.core.models import TermSheetAnalysis, AnalysisRedFlag, AnalysisScenario


class AnalysisRedFlagSerializer(serializers.ModelSerializer):
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
            'created_at',
        ]


class AnalysisScenarioSerializer(serializers.ModelSerializer):
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
            'created_at',
        ]


class TermSheetAnalysisListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list view.
    """
    red_flags_count = serializers.IntegerField(read_only=True)
    scenarios_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = TermSheetAnalysis
        fields = [
            'id',
            'file_name',
            'status',
            'investment_amount',
            'pre_money_valuation',
            'post_money_valuation',
            'dilution_pct',
            'red_flags_count',
            'scenarios_count',
            'ai_confidence_score',
            'created_at',
            'completed_at',
        ]


class TermSheetAnalysisDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer with all details and nested relationships.
    """
    red_flags = AnalysisRedFlagSerializer(many=True, read_only=True)
    scenarios = AnalysisScenarioSerializer(many=True, read_only=True)
    
    # Add computed fields
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
            'error_message',
            'created_at',
            'updated_at',
            'completed_at',
            
            # Computed summary objects
            'deal_summary',
            'dilution_analysis',
            'key_terms',
            
            # Nested relationships
            'red_flags',
            'scenarios',
            
            # AI analysis
            'plain_english_explanation',
            'ai_confidence_score',
        ]
    
    def get_deal_summary(self, obj):
        return {
            'pre_money_valuation': str(obj.pre_money_valuation) if obj.pre_money_valuation else None,
            'investment_amount': str(obj.investment_amount) if obj.investment_amount else None,
            'post_money_valuation': str(obj.post_money_valuation) if obj.post_money_valuation else None,
            'new_shares_issued': obj.new_shares_issued,
            'price_per_share': str(obj.price_per_share) if obj.price_per_share else None,
            'option_pool_increase_pct': str(obj.option_pool_increase_pct) if obj.option_pool_increase_pct else None,
        }
    
    def get_dilution_analysis(self, obj):
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
        return {
            'liquidation_preference_multiple': str(obj.liquidation_preference_multiple) if obj.liquidation_preference_multiple else None,
            'liquidation_preference_type': obj.liquidation_preference_type,
            'anti_dilution_type': obj.anti_dilution_type,
            'board_composition': obj.board_composition,
        }


class TermSheetAnalysisCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new analysis (file upload).
    """
    term_sheet_file = serializers.FileField(required=True)
    user_notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = TermSheetAnalysis
        fields = ['term_sheet_file', 'user_notes']
    
    def validate_term_sheet_file(self, value):
        # Validate file type
        if not value.name.endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are supported.")
        
        # Validate file size (10MB max)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 10MB.")
        
        return value
    
    def create(self, validated_data):
        # Get tenant and user from context
        request = self.context['request']
        tenant = request.user.tenant
        
        # Create analysis record
        file = validated_data['term_sheet_file']
        analysis = TermSheetAnalysis.objects.create(
            tenant=tenant,
            created_by=request.user,
            term_sheet_file=file,
            file_name=file.name,
            file_size_bytes=file.size,
            user_notes=validated_data.get('user_notes', ''),
            status='UPLOADED'
        )
        
        return analysis
```

**File:** `apps/api/views/deal_desk.py` (new file)

**Task 1.5: Create API Views**

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.core.models import TermSheetAnalysis
from apps.api.serializers import (
    TermSheetAnalysisListSerializer,
    TermSheetAnalysisDetailSerializer,
    TermSheetAnalysisCreateSerializer,
)
from apps.core.services.deal_desk_analyzer import DealDeskAnalyzer


class DealDeskViewSet(viewsets.ModelViewSet):
    """
    API endpoints for Deal Desk term sheet analysis.
    
    Endpoints:
    - POST /api/v1/deal-desk/analyze/ - Upload and analyze term sheet
    - GET /api/v1/deal-desk/analyses/ - List all analyses for tenant
    - GET /api/v1/deal-desk/analyses/{id}/ - Get detailed analysis
    - GET /api/v1/deal-desk/analyses/{id}/pdf/ - Download PDF report
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Multi-tenant filtering
        return TermSheetAnalysis.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('created_by').prefetch_related('red_flags', 'scenarios')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TermSheetAnalysisCreateSerializer
        elif self.action == 'list':
            return TermSheetAnalysisListSerializer
        else:
            return TermSheetAnalysisDetailSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Upload term sheet PDF and start analysis.
        
        Usage limit enforcement:
        - Free tier: 1 analysis total
        - Starter tier: 3 analyses per year
        - Professional tier: Unlimited
        """
        
        # Check usage limits
        tenant = request.user.tenant
        usage_check = self._check_usage_limit(tenant)
        
        if not usage_check['allowed']:
            return Response(
                {
                    'error': 'usage_limit_reached',
                    'message': usage_check['message'],
                    'current_plan': usage_check['current_plan'],
                    'upgrade_url': '/billing/upgrade',
                },
                status=status.HTTP_402_PAYMENT_REQUIRED
            )
        
        # Create analysis record
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        analysis = serializer.save()
        
        # Trigger async analysis (Celery task or sync for MVP)
        try:
            analyzer = DealDeskAnalyzer(analysis)
            analyzer.process()
        except Exception as e:
            analysis.status = 'FAILED'
            analysis.error_message = str(e)
            analysis.save()
        
        # Return created analysis
        response_serializer = TermSheetAnalysisDetailSerializer(analysis)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    def _check_usage_limit(self, tenant):
        """
        Check if tenant has remaining analyses available.
        """
        from datetime import datetime, timedelta
        
        # Get tenant's subscription plan (assuming you have this)
        plan = tenant.subscription_plan  # 'FREE', 'STARTER', 'PROFESSIONAL', 'ENTERPRISE'
        
        # Define limits
        limits = {
            'FREE': {'total': 1, 'period': None},
            'STARTER': {'total': 3, 'period': 'year'},
            'PROFESSIONAL': {'total': -1, 'period': None},  # -1 = unlimited
            'ENTERPRISE': {'total': -1, 'period': None},
        }
        
        plan_limit = limits.get(plan, limits['FREE'])
        
        # Unlimited plans
        if plan_limit['total'] == -1:
            return {'allowed': True}
        
        # Count existing analyses
        if plan_limit['period'] == 'year':
            # Count analyses in the last 365 days
            one_year_ago = datetime.now() - timedelta(days=365)
            count = TermSheetAnalysis.objects.filter(
                tenant=tenant,
                created_at__gte=one_year_ago
            ).count()
        else:
            # Count all-time analyses
            count = TermSheetAnalysis.objects.filter(tenant=tenant).count()
        
        # Check limit
        if count >= plan_limit['total']:
            return {
                'allowed': False,
                'message': f"You've used {count}/{plan_limit['total']} analyses. Upgrade to analyze more term sheets.",
                'current_plan': plan,
            }
        
        return {'allowed': True}
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """
        Generate and download PDF report.
        
        GET /api/v1/deal-desk/analyses/{id}/pdf/
        """
        analysis = self.get_object()
        
        # TODO: Implement PDF generation
        # For now, return not implemented
        return Response(
            {'message': 'PDF generation coming in Sprint 1C'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )
```

**File:** `apps/api/urls.py` (update)

**Task 1.6: Register URLs**

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.api.views.deal_desk import DealDeskViewSet

router = DefaultRouter()
router.register(r'deal-desk/analyses', DealDeskViewSet, basename='deal-desk')

urlpatterns = [
    path('', include(router.urls)),
    # ... existing URLs
]
```

**Testing Checklist (Days 2-3):**
- [ ] Can call POST /api/v1/deal-desk/analyses/ with PDF file
- [ ] Analysis record created with status='UPLOADED'
- [ ] Can call GET /api/v1/deal-desk/analyses/ to list analyses
- [ ] Can call GET /api/v1/deal-desk/analyses/{id}/ to get details
- [ ] Usage limit returns 402 error when exceeded
- [ ] Multi-tenant isolation works (can't see other tenants' analyses)

---

### Sprint 1C: AI Integration (Day 4)

**File:** `apps/core/services/deal_desk_analyzer.py` (new file)

**Task 1.7: Create DealDeskAnalyzer Service**

```python
import openai
import json
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from apps.core.models import TermSheetAnalysis, AnalysisRedFlag, AnalysisScenario


class DealDeskAnalyzer:
    """
    Orchestrates the term sheet analysis process:
    1. Extract text from PDF
    2. Get current cap table context
    3. Call OpenAI API for analysis
    4. Parse and store results
    """
    
    def __init__(self, analysis: TermSheetAnalysis):
        self.analysis = analysis
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def process(self):
        """
        Main processing method.
        """
        try:
            # Step 1: Extract text from PDF
            self.analysis.status = 'EXTRACTING'
            self.analysis.save()
            term_sheet_text = self._extract_pdf_text()
            
            # Step 2: Get cap table context
            cap_table_data = self._get_cap_table_context()
            
            # Step 3: Call OpenAI for analysis
            self.analysis.status = 'ANALYZING'
            self.analysis.save()
            ai_response = self._call_openai(term_sheet_text, cap_table_data)
            
            # Step 4: Parse and store results
            self._store_results(ai_response)
            
            # Mark as completed
            self.analysis.status = 'COMPLETED'
            self.analysis.completed_at = timezone.now()
            self.analysis.save()
            
        except Exception as e:
            self.analysis.status = 'FAILED'
            self.analysis.error_message = str(e)
            self.analysis.save()
            raise
    
    def _extract_pdf_text(self) -> str:
        """
        Extract text from uploaded PDF.
        Uses pdfplumber (preferred) with PyPDF2 fallback.
        """
        import pdfplumber
        
        pdf_path = self.analysis.term_sheet_file.path
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ''
                for page in pdf.pages:
                    text += page.extract_text() + '\n\n'
                return text.strip()
        except Exception as e:
            # Fallback to PyPDF2
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                for page in reader.pages:
                    text += page.extract_text() + '\n\n'
                return text.strip()
    
    def _get_cap_table_context(self) -> dict:
        """
        Get current cap table data for dilution calculation.
        """
        from apps.core.models import Shareholder, Holding
        
        tenant = self.analysis.tenant
        
        # Get all shareholders and their holdings
        shareholders = Shareholder.objects.filter(tenant=tenant)
        holdings = Holding.objects.filter(shareholder__tenant=tenant)
        
        # Calculate totals
        total_shares = sum(h.share_quantity for h in holdings)
        
        # Identify founder shares (assuming created_by is a founder)
        founder_user = self.analysis.created_by
        founder_shareholder = shareholders.filter(user=founder_user).first()
        
        if founder_shareholder:
            founder_holdings = holdings.filter(shareholder=founder_shareholder)
            founder_shares = sum(h.share_quantity for h in founder_holdings)
            founder_ownership_pct = (founder_shares / total_shares * 100) if total_shares > 0 else 0
        else:
            founder_shares = 0
            founder_ownership_pct = 0
        
        return {
            'total_shares': total_shares,
            'founder_shares': founder_shares,
            'founder_ownership_pct': round(founder_ownership_pct, 2),
            'shareholder_count': shareholders.count(),
        }
    
    def _call_openai(self, term_sheet_text: str, cap_table_data: dict) -> dict:
        """
        Call OpenAI API with the full prompt.
        """
        # Import the production prompt from separate file
        from apps.core.services.deal_desk_prompt import DEAL_DESK_PROMPT
        
        # Format prompt with data
        prompt = DEAL_DESK_PROMPT.format(
            term_sheet_text=term_sheet_text,
            total_shares=cap_table_data['total_shares'],
            founder_shares=cap_table_data['founder_shares'],
            founder_ownership_pct=cap_table_data['founder_ownership_pct'],
        )
        
        # Call OpenAI
        response = self.openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",  # or "gpt-4o" when available
            messages=[
                {"role": "system", "content": "You are a senior startup advisor analyzing term sheets."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for consistency
            response_format={"type": "json_object"}
        )
        
        # Parse JSON response
        ai_response = json.loads(response.choices[0].message.content)
        return ai_response
    
    def _store_results(self, ai_response: dict):
        """
        Parse AI response and store in database.
        """
        # Store full response
        self.analysis.ai_full_response = ai_response
        
        # Extract and store deal summary
        deal_summary = ai_response.get('deal_summary', {})
        self.analysis.pre_money_valuation = Decimal(str(deal_summary.get('pre_money_valuation', 0)))
        self.analysis.investment_amount = Decimal(str(deal_summary.get('investment_amount', 0)))
        self.analysis.post_money_valuation = Decimal(str(deal_summary.get('post_money_valuation', 0)))
        self.analysis.new_shares_issued = deal_summary.get('new_shares_issued')
        
        # Extract dilution analysis
        dilution = ai_response.get('dilution_analysis', {})
        self.analysis.founder_shares_before = dilution.get('founder_shares_before')
        self.analysis.total_shares_before = dilution.get('total_shares_before')
        self.analysis.founder_ownership_before_pct = Decimal(str(dilution.get('founder_ownership_before_pct', 0)))
        self.analysis.founder_shares_after = dilution.get('founder_shares_after')
        self.analysis.total_shares_after = dilution.get('total_shares_after')
        self.analysis.founder_ownership_after_pct = Decimal(str(dilution.get('founder_ownership_after_pct', 0)))
        self.analysis.dilution_pct = Decimal(str(dilution.get('dilution_pct', 0)))
        
        # Extract key terms
        key_terms = ai_response.get('key_terms', {})
        self.analysis.liquidation_preference_multiple = Decimal(str(key_terms.get('liquidation_preference_multiple', 1.0)))
        self.analysis.liquidation_preference_type = key_terms.get('liquidation_preference_type')
        self.analysis.anti_dilution_type = key_terms.get('anti_dilution_type')
        self.analysis.board_composition = key_terms.get('board_composition')
        
        # Store plain English explanation
        self.analysis.plain_english_explanation = ai_response.get('plain_english_explanation', '')
        self.analysis.ai_confidence_score = ai_response.get('ai_confidence_score', 0.0)
        
        self.analysis.save()
        
        # Store red flags
        for flag_data in ai_response.get('red_flags', []):
            AnalysisRedFlag.objects.create(
                analysis=self.analysis,
                flag_type=flag_data.get('type', 'unknown'),
                severity=flag_data.get('severity', 'MEDIUM'),
                title=flag_data.get('title', ''),
                description=flag_data.get('description', ''),
                prevalence=flag_data.get('prevalence', ''),
                recommendation=flag_data.get('recommendation', ''),
            )
        
        # Store scenarios
        for scenario_data in ai_response.get('alternative_scenarios', []):
            AnalysisScenario.objects.create(
                analysis=self.analysis,
                scenario_label=scenario_data.get('label', 'Scenario'),
                title=scenario_data.get('title', ''),
                description=scenario_data.get('description', ''),
                new_valuation=Decimal(str(scenario_data.get('new_valuation', 0))) if scenario_data.get('new_valuation') else None,
                new_dilution_pct=Decimal(str(scenario_data.get('new_dilution_pct', 0))) if scenario_data.get('new_dilution_pct') else None,
                likelihood_of_acceptance=scenario_data.get('likelihood', ''),
            )
```

**File:** `apps/core/services/deal_desk_prompt.py` (new file)

**Task 1.8: Create OpenAI Prompt Template**

*Note: Full production prompt will be in Document 4. For now, placeholder:*

```python
DEAL_DESK_PROMPT = """
You are analyzing a term sheet for a startup founder.

CURRENT CAP TABLE:
- Total shares outstanding: {total_shares}
- Founder shares: {founder_shares}
- Founder ownership: {founder_ownership_pct}%

TERM SHEET TEXT:
{term_sheet_text}

Analyze the term sheet and respond with JSON in this exact format:
{{
  "deal_summary": {{
    "pre_money_valuation": <number>,
    "investment_amount": <number>,
    "post_money_valuation": <number>,
    "new_shares_issued": <number>,
    "price_per_share": <number>
  }},
  "dilution_analysis": {{
    "founder_shares_before": {founder_shares},
    "total_shares_before": {total_shares},
    "founder_ownership_before_pct": {founder_ownership_pct},
    "founder_shares_after": <calculated>,
    "total_shares_after": <calculated>,
    "founder_ownership_after_pct": <calculated>,
    "dilution_pct": <calculated>
  }},
  "key_terms": {{
    "liquidation_preference_multiple": <number>,
    "liquidation_preference_type": "<participating|non-participating>",
    "anti_dilution_type": "<full_ratchet|weighted_average|none>",
    "board_composition": {{"founder": <number>, "investor": <number>}}
  }},
  "red_flags": [
    {{
      "type": "full_ratchet_anti_dilution",
      "severity": "HIGH",
      "title": "Full Ratchet Anti-Dilution Detected",
      "description": "This term sheet includes...",
      "prevalence": "Only 5% of seed deals",
      "recommendation": "Counter with weighted-average anti-dilution"
    }}
  ],
  "alternative_scenarios": [
    {{
      "label": "Scenario A",
      "title": "Counter with Standard Terms",
      "description": "Propose weighted-average anti-dilution...",
      "new_dilution_pct": -10.0,
      "likelihood": "High"
    }}
  ],
  "plain_english_explanation": "This term sheet offers...",
  "ai_confidence_score": 0.92
}}

Output JSON only, no markdown.
"""
```

**Testing Checklist (Day 4):**
- [ ] PDF text extraction works (test with sample term sheet)
- [ ] OpenAI API call succeeds (check settings.OPENAI_API_KEY is set)
- [ ] AI response is valid JSON
- [ ] Results stored in database (analysis, red_flags, scenarios)
- [ ] Analysis status progresses: UPLOADED → EXTRACTING → ANALYZING → COMPLETED

---

## 🎨 PHASE 2: FRONTEND (Days 5-10)

### Sprint 2A: Upload Page (Days 5-6)

**File:** `client/src/pages/DealDesk/DealDeskUpload.tsx` (new file)

**Task 2.1: Create Upload Component**

```typescript
import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react';
import { apiClient } from '../../services/api';
import { useNavigate } from 'react-router-dom';

interface UploadState {
  file: File | null;
  uploading: boolean;
  error: string | null;
  progress: number;
}

export const DealDeskUpload: React.FC = () => {
  const navigate = useNavigate();
  const [state, setState] = useState<UploadState>({
    file: null,
    uploading: false,
    error: null,
    progress: 0,
  });

  const onDrop = (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    
    // Validate file
    if (!file) return;
    
    if (!file.name.endsWith('.pdf')) {
      setState(prev => ({ ...prev, error: 'Only PDF files are supported' }));
      return;
    }
    
    if (file.size > 10 * 1024 * 1024) {
      setState(prev => ({ ...prev, error: 'File must be less than 10MB' }));
      return;
    }
    
    setState(prev => ({ ...prev, file, error: null }));
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    maxSize: 10 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!state.file) return;

    setState(prev => ({ ...prev, uploading: true, error: null }));

    try {
      const formData = new FormData();
      formData.append('term_sheet_file', state.file);

      const response = await apiClient.post('/api/v1/deal-desk/analyses/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const progress = progressEvent.total
            ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
            : 0;
          setState(prev => ({ ...prev, progress }));
        },
      });

      // Navigate to analysis page
      navigate(`/deal-desk/analyses/${response.data.id}`);
      
    } catch (error: any) {
      if (error.response?.status === 402) {
        // Usage limit reached
        setState(prev => ({
          ...prev,
          uploading: false,
          error: error.response.data.message,
        }));
      } else {
        setState(prev => ({
          ...prev,
          uploading: false,
          error: 'Upload failed. Please try again.',
        }));
      }
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Deal Desk</h1>
        <p className="mt-2 text-gray-600">
          Upload your term sheet to get AI-powered analysis in 60 seconds
        </p>
      </div>

      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
          ${state.file ? 'bg-green-50 border-green-500' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        {!state.file ? (
          <>
            <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              {isDragActive ? 'Drop your term sheet here' : 'Drag & drop your term sheet PDF'}
            </p>
            <p className="text-sm text-gray-500">
              or click to browse • Maximum 10MB
            </p>
          </>
        ) : (
          <>
            <FileText className="mx-auto h-12 w-12 text-green-600 mb-4" />
            <p className="text-lg font-medium text-gray-900 mb-2">
              {state.file.name}
            </p>
            <p className="text-sm text-gray-500">
              {(state.file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </>
        )}
      </div>

      {/* Error Message */}
      {state.error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
          <AlertCircle className="h-5 w-5 text-red-600 mr-3 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-900">Upload Error</p>
            <p className="text-sm text-red-700 mt-1">{state.error}</p>
          </div>
        </div>
      )}

      {/* Upload Button */}
      {state.file && !state.uploading && (
        <button
          onClick={handleUpload}
          className="mt-6 w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium
                     hover:bg-blue-700 transition-colors duration-200"
        >
          Analyze Term Sheet
        </button>
      )}

      {/* Upload Progress */}
      {state.uploading && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Uploading & analyzing...</span>
            <span className="text-sm text-gray-600">{state.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${state.progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            This usually takes 60 seconds
          </p>
        </div>
      )}

      {/* Info Cards */}
      <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 bg-gray-50 rounded-lg">
          <CheckCircle className="h-8 w-8 text-green-600 mb-3" />
          <h3 className="font-semibold text-gray-900 mb-2">Instant Analysis</h3>
          <p className="text-sm text-gray-600">
            Get your analysis in ~60 seconds, not 2 weeks
          </p>
        </div>
        
        <div className="p-6 bg-gray-50 rounded-lg">
          <CheckCircle className="h-8 w-8 text-green-600 mb-3" />
          <h3 className="font-semibold text-gray-900 mb-2">Red Flag Detection</h3>
          <p className="text-sm text-gray-600">
            AI identifies founder-hostile terms automatically
          </p>
        </div>
        
        <div className="p-6 bg-gray-50 rounded-lg">
          <CheckCircle className="h-8 w-8 text-green-600 mb-3" />
          <h3 className="font-semibold text-gray-900 mb-2">Negotiation Scenarios</h3>
          <p className="text-sm text-gray-600">
            Get 3 alternative scenarios to consider
          </p>
        </div>
      </div>
    </div>
  );
};
```

**Testing Checklist (Days 5-6):**
- [ ] Drag-and-drop works
- [ ] File validation works (PDF only, <10MB)
- [ ] Upload progress shows
- [ ] Error handling works (usage limit, network errors)
- [ ] Navigates to analysis page after upload

---

### Sprint 2B: Analysis Dashboard (Days 7-8)

**File:** `client/src/pages/DealDesk/DealDeskDashboard.tsx` (new file)

```typescript
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { apiClient } from '../../services/api';

interface Analysis {
  id: string;
  file_name: string;
  status: 'UPLOADED' | 'EXTRACTING' | 'ANALYZING' | 'COMPLETED' | 'FAILED';
  investment_amount: string | null;
  pre_money_valuation: string | null;
  dilution_pct: string | null;
  red_flags_count: number;
  ai_confidence_score: number | null;
  created_at: string;
  completed_at: string | null;
}

export const DealDeskDashboard: React.FC = () => {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalyses();
    const interval = setInterval(fetchAnalyses, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchAnalyses = async () => {
    try {
      const response = await apiClient.get('/api/v1/deal-desk/analyses/');
      setAnalyses(response.data.results || response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch analyses', error);
      setLoading(false);
    }
  };

  const getStatusBadge = (status: Analysis['status']) => {
    const badges = {
      UPLOADED: { icon: Clock, text: 'Uploaded', color: 'bg-gray-100 text-gray-800' },
      EXTRACTING: { icon: Clock, text: 'Extracting...', color: 'bg-blue-100 text-blue-800' },
      ANALYZING: { icon: Clock, text: 'Analyzing...', color: 'bg-blue-100 text-blue-800' },
      COMPLETED: { icon: CheckCircle, text: 'Completed', color: 'bg-green-100 text-green-800' },
      FAILED: { icon: XCircle, text: 'Failed', color: 'bg-red-100 text-red-800' },
    };

    const badge = badges[status];
    const Icon = badge.icon;

    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${badge.color}`}>
        <Icon className="h-4 w-4 mr-1" />
        {badge.text}
      </span>
    );
  };

  if (loading) {
    return <div className="p-6">Loading...</div>;
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Deal Desk</h1>
          <p className="mt-2 text-gray-600">Your term sheet analyses</p>
        </div>
        <Link
          to="/deal-desk/upload"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700"
        >
          + New Analysis
        </Link>
      </div>

      {analyses.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No analyses yet</h3>
          <p className="text-gray-600 mb-6">Upload your first term sheet to get started</p>
          <Link
            to="/deal-desk/upload"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700"
          >
            Upload Term Sheet
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {analyses.map((analysis) => (
            <div
              key={analysis.id}
              className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <FileText className="h-5 w-5 text-gray-400" />
                    <h3 className="text-lg font-semibold text-gray-900">
                      {analysis.file_name}
                    </h3>
                    {getStatusBadge(analysis.status)}
                  </div>

                  {analysis.status === 'COMPLETED' && (
                    <div className="mt-4 grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Investment</p>
                        <p className="font-semibold text-gray-900">
                          ${Number(analysis.investment_amount).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Pre-Money</p>
                        <p className="font-semibold text-gray-900">
                          ${Number(analysis.pre_money_valuation).toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Dilution</p>
                        <p className="font-semibold text-gray-900">
                          {analysis.dilution_pct}%
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Red Flags</p>
                        <p className={`font-semibold ${
                          analysis.red_flags_count > 0 ? 'text-red-600' : 'text-green-600'
                        }`}>
                          {analysis.red_flags_count === 0 ? 'None' : analysis.red_flags_count}
                        </p>
                      </div>
                    </div>
                  )}

                  <p className="text-sm text-gray-500 mt-3">
                    Created {new Date(analysis.created_at).toLocaleDateString()}
                  </p>
                </div>

                {analysis.status === 'COMPLETED' && (
                  <Link
                    to={`/deal-desk/analyses/${analysis.id}`}
                    className="ml-4 bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700"
                  >
                    View Report
                  </Link>
                )}

                {(analysis.status === 'EXTRACTING' || analysis.status === 'ANALYZING') && (
                  <div className="ml-4 text-blue-600 px-4 py-2">
                    Processing...
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

**Testing Checklist (Days 7-8):**
- [ ] Dashboard loads and displays analyses
- [ ] Status badges show correctly
- [ ] Polling updates status in real-time
- [ ] "New Analysis" button navigates to upload page
- [ ] "View Report" button navigates to detail page

---

### Sprint 2C: Analysis Report (Days 9-10)

**File:** `client/src/pages/DealDesk/DealDeskReport.tsx` (new file)

*Note: This is a large component. For brevity, showing key sections:*

```typescript
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { AlertCircle, CheckCircle, Download } from 'lucide-react';
import { apiClient } from '../../services/api';

interface AnalysisDetail {
  id: string;
  file_name: string;
  status: string;
  deal_summary: {
    pre_money_valuation: string;
    investment_amount: string;
    post_money_valuation: string;
    new_shares_issued: number;
    price_per_share: string;
  };
  dilution_analysis: {
    founder_shares_before: number;
    total_shares_before: number;
    founder_ownership_before_pct: string;
    founder_shares_after: number;
    total_shares_after: number;
    founder_ownership_after_pct: string;
    dilution_pct: string;
  };
  red_flags: Array<{
    id: string;
    severity: string;
    title: string;
    description: string;
    prevalence: string;
    recommendation: string;
  }>;
  scenarios: Array<{
    id: string;
    scenario_label: string;
    title: string;
    description: string;
    likelihood_of_acceptance: string;
  }>;
  plain_english_explanation: string;
  ai_confidence_score: number;
}

export const DealDeskReport: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalysis();
  }, [id]);

  const fetchAnalysis = async () => {
    try {
      const response = await apiClient.get(`/api/v1/deal-desk/analyses/${id}/`);
      setAnalysis(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch analysis', error);
      setLoading(false);
    }
  };

  if (loading || !analysis) {
    return <div className="p-6">Loading...</div>;
  }

  // Prepare pie chart data
  const dilutionData = [
    {
      name: 'Founder',
      value: parseFloat(analysis.dilution_analysis.founder_ownership_after_pct),
      color: '#3B82F6',
    },
    {
      name: 'Investors',
      value: 100 - parseFloat(analysis.dilution_analysis.founder_ownership_after_pct),
      color: '#10B981',
    },
  ];

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Analysis: {analysis.file_name}
        </h1>
        <button className="text-blue-600 hover:text-blue-700 font-medium">
          <Download className="inline h-4 w-4 mr-1" />
          Download PDF Report
        </button>
      </div>

      {/* Deal Summary */}
      <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">💰 Deal Summary</h2>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-gray-500">Pre-Money Valuation</p>
            <p className="text-2xl font-bold text-gray-900">
              ${Number(analysis.deal_summary.pre_money_valuation).toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Investment Amount</p>
            <p className="text-2xl font-bold text-gray-900">
              ${Number(analysis.deal_summary.investment_amount).toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Post-Money Valuation</p>
            <p className="text-2xl font-bold text-gray-900">
              ${Number(analysis.deal_summary.post_money_valuation).toLocaleString()}
            </p>
          </div>
        </div>
      </section>

      {/* Dilution Chart */}
      <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">📉 Dilution Impact</h2>
        <div className="grid grid-cols-2 gap-8">
          <div>
            <h3 className="font-semibold text-gray-700 mb-3">Ownership Breakdown</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={dilutionData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  dataKey="value"
                  label={(entry) => `${entry.name}: ${entry.value.toFixed(1)}%`}
                >
                  {dilutionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div>
            <h3 className="font-semibold text-gray-700 mb-3">Impact Summary</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Before Deal:</span>
                <span className="font-semibold">
                  {analysis.dilution_analysis.founder_ownership_before_pct}%
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">After Deal:</span>
                <span className="font-semibold">
                  {analysis.dilution_analysis.founder_ownership_after_pct}%
                </span>
              </div>
              <div className="flex justify-between pt-2 border-t border-gray-200">
                <span className="text-gray-600">Dilution:</span>
                <span className="font-semibold text-red-600">
                  {analysis.dilution_analysis.dilution_pct}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Red Flags */}
      {analysis.red_flags.length > 0 && (
        <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            🚨 Red Flags ({analysis.red_flags.length} detected)
          </h2>
          <div className="space-y-4">
            {analysis.red_flags.map((flag) => (
              <div
                key={flag.id}
                className={`p-4 rounded-lg border-l-4 ${
                  flag.severity === 'HIGH' || flag.severity === 'CRITICAL'
                    ? 'bg-red-50 border-red-500'
                    : flag.severity === 'MEDIUM'
                    ? 'bg-yellow-50 border-yellow-500'
                    : 'bg-blue-50 border-blue-500'
                }`}
              >
                <div className="flex items-start">
                  <AlertCircle className={`h-5 w-5 mt-0.5 mr-3 ${
                    flag.severity === 'HIGH' || flag.severity === 'CRITICAL'
                      ? 'text-red-600'
                      : flag.severity === 'MEDIUM'
                      ? 'text-yellow-600'
                      : 'text-blue-600'
                  }`} />
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1">
                      {flag.severity} RISK: {flag.title}
                    </h3>
                    <p className="text-sm text-gray-700 mb-2">{flag.description}</p>
                    {flag.prevalence && (
                      <p className="text-sm text-gray-600 italic mb-2">
                        Prevalence: {flag.prevalence}
                      </p>
                    )}
                    <p className="text-sm font-medium text-gray-900">
                      💡 Recommendation: {flag.recommendation}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Alternative Scenarios */}
      <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">💡 Alternative Scenarios</h2>
        <div className="space-y-4">
          {analysis.scenarios.map((scenario) => (
            <div key={scenario.id} className="p-4 bg-gray-50 rounded-lg">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-gray-900">{scenario.scenario_label}: {scenario.title}</h3>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  scenario.likelihood_of_acceptance === 'High'
                    ? 'bg-green-100 text-green-800'
                    : scenario.likelihood_of_acceptance === 'Medium'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  Likelihood: {scenario.likelihood_of_acceptance}
                </span>
              </div>
              <p className="text-sm text-gray-700">{scenario.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Plain English Summary */}
      <section className="bg-blue-50 rounded-lg border border-blue-200 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">📝 Plain English Summary</h2>
        <p className="text-gray-700 whitespace-pre-line leading-relaxed">
          {analysis.plain_english_explanation}
        </p>
        <div className="mt-4 pt-4 border-t border-blue-200 text-sm text-gray-600">
          AI Confidence: {(analysis.ai_confidence_score * 100).toFixed(0)}%
        </div>
      </section>
    </div>
  );
};
```

**Testing Checklist (Days 9-10):**
- [ ] Report page loads with analysis details
- [ ] Pie chart displays correctly
- [ ] Red flags show with correct severity colors
- [ ] Scenarios display with likelihood badges
- [ ] Plain English summary is readable

---

## 🚀 PHASE 3: INTEGRATION & POLISH (Days 11-14)

### Sprint 3A: Routing & Navigation (Day 11)

**File:** `client/src/App.tsx` (update)

**Task 3.1: Add Routes**

```typescript
import { Routes, Route } from 'react-router-dom';
import { DealDeskUpload } from './pages/DealDesk/DealDeskUpload';
import { DealDeskDashboard } from './pages/DealDesk/DealDeskDashboard';
import { DealDeskReport } from './pages/DealDesk/DealDeskReport';

// Add to existing routes
<Routes>
  {/* Existing routes */}
  
  {/* Deal Desk routes */}
  <Route path="/deal-desk" element={<DealDeskDashboard />} />
  <Route path="/deal-desk/upload" element={<DealDeskUpload />} />
  <Route path="/deal-desk/analyses/:id" element={<DealDeskReport />} />
</Routes>
```

**Task 3.2: Add Nav Link**

```typescript
// In your main navigation component
<NavLink to="/deal-desk" className="nav-link">
  📊 Deal Desk
</NavLink>
```

---

### Sprint 3B: Error Handling & Edge Cases (Days 12-13)

**Task 3.3: Backend Error Handling**

```python
# apps/api/views/deal_desk.py

# Add comprehensive error handling
try:
    analyzer = DealDeskAnalyzer(analysis)
    analyzer.process()
except PDFExtractionError as e:
    analysis.status = 'FAILED'
    analysis.error_message = 'Could not extract text from PDF. Please ensure it is not password-protected.'
    analysis.save()
except OpenAIAPIError as e:
    analysis.status = 'FAILED'
    analysis.error_message = 'AI analysis temporarily unavailable. Please try again later.'
    analysis.save()
except Exception as e:
    analysis.status = 'FAILED'
    analysis.error_message = f'Unexpected error: {str(e)}'
    analysis.save()
```

**Task 3.4: Frontend Error States**

```typescript
// Add error states to all pages
{analysis.status === 'FAILED' && (
  <div className="bg-red-50 border border-red-200 rounded-lg p-6">
    <h3 className="text-lg font-semibold text-red-900 mb-2">Analysis Failed</h3>
    <p className="text-red-700">{analysis.error_message}</p>
    <button 
      onClick={() => navigate('/deal-desk/upload')}
      className="mt-4 bg-red-600 text-white px-4 py-2 rounded"
    >
      Try Again
    </button>
  </div>
)}
```

---

### Sprint 3C: Testing & QA (Day 14)

**Task 3.5: End-to-End Testing**

Test user flow:
1. Upload term sheet PDF
2. Wait for analysis to complete
3. View report with dilution chart
4. Check red flags
5. Review scenarios
6. Download PDF report (if implemented)

**Task 3.6: Usage Limit Testing**

Test freemium enforcement:
1. Free tier: Upload 1 term sheet → success
2. Free tier: Upload 2nd term sheet → 402 error
3. Starter tier: Upload 3 term sheets in year → success
4. Starter tier: Upload 4th term sheet → 402 error

**Testing Checklist (Day 14):**
- [ ] Full user flow works end-to-end
- [ ] Usage limits enforced correctly
- [ ] Error handling works for all failure modes
- [ ] Multi-tenant isolation verified (can't see other tenants' data)
- [ ] Performance acceptable (<60 seconds per analysis)

---

## 📦 DELIVERABLES

### At End of 2-Week Sprint:

**Backend (Django):**
- ✅ 3 new models (TermSheetAnalysis, AnalysisRedFlag, AnalysisScenario)
- ✅ API endpoints for upload, list, detail
- ✅ OpenAI integration with production prompt
- ✅ Usage limit enforcement (Stripe tiers)
- ✅ Multi-tenant isolation

**Frontend (React):**
- ✅ Upload page with drag-and-drop
- ✅ Dashboard with analysis list
- ✅ Detailed report with charts
- ✅ Error handling and loading states

**AI Engine:**
- ✅ PDF text extraction (pdfplumber + PyPDF2 fallback)
- ✅ OpenAI GPT-4 Turbo integration
- ✅ Structured JSON output parsing
- ✅ Red flag detection
- ✅ Scenario generation

**Infrastructure:**
- ✅ S3 file storage for PDFs
- ✅ PostgreSQL schema migrations
- ✅ API authentication (JWT)
- ✅ CORS configuration

---

## 🔧 DEPLOYMENT CHECKLIST

Before deploying to production:

**Environment Variables:**
```bash
# Add to AWS Parameter Store or .env
OPENAI_API_KEY=sk-...
AWS_STORAGE_BUCKET_NAME=tableicty-term-sheets
```

**Database Migrations:**
```bash
python manage.py migrate
```

**Frontend Build:**
```bash
cd client
npm run build
aws s3 sync dist/ s3://tableicty-frontend/
aws cloudfront create-invalidation --distribution-id XXX --paths "/*"
```

**Backend Deploy:**
```bash
git push origin main
# App Runner auto-deploys
```

---

## 📊 SUCCESS METRICS

Track these after launch:

**Usage Metrics:**
- [ ] Term sheets analyzed per week
- [ ] Average analysis time (<60 seconds target)
- [ ] AI confidence score average (>85% target)
- [ ] Completion rate (uploaded → completed)

**Business Metrics:**
- [ ] Free-to-paid conversion rate (20% target)
- [ ] Usage limit upgrade triggers
- [ ] Customer satisfaction (NPS)

**Technical Metrics:**
- [ ] API response time (<2 seconds)
- [ ] Error rate (<5%)
- [ ] OpenAI API cost per analysis
- [ ] S3 storage growth

---

## ❓ QUESTIONS FOR APP BUILDER

Before starting, clarify:

1. **OpenAI API Key:** Do you have GPT-4 API access? (Required for production prompt)
2. **Subscription Model:** Do you have a `subscription_plan` field on Tenant model?
3. **File Storage:** Is AWS S3 already configured for file uploads?
4. **Celery:** Do you want async processing (Celery) or sync for MVP?
5. **PDF Library:** Prefer pdfplumber, PyPDF2, or both (fallback)?

---

## 🎯 NEXT STEPS AFTER SPRINT

Once MVP is live:

**Week 3-4: Refinement**
- [ ] PDF report generation (jsPDF or Puppeteer)
- [ ] Email notifications when analysis completes
- [ ] Shareholder-specific dilution breakdown (if multiple co-founders)
- [ ] Historical comparison (compare multiple term sheets)

**Month 2: Advanced Features**
- [ ] Custom prompts for different deal types (SAFE, convertible note, equity)
- [ ] Integration with cap table (auto-update after deal closes)
- [ ] Collaboration features (share analysis with co-founders)
- [ ] Export to Google Sheets / Excel

---

**END OF APP BUILDER SPRINT SPEC**

*This document breaks down the 2-week build into testable increments. Refer back when blocked.*

---
