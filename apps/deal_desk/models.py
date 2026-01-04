from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class TermSheetAnalysis(models.Model):
    """
    Main model for term sheet analysis.
    Stores uploaded PDF, extracted data, and AI-generated analysis.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant = models.ForeignKey(
        'core.Tenant',
        on_delete=models.CASCADE,
        related_name='term_sheet_analyses',
        db_index=True
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_analyses'
    )
    
    term_sheet_file = models.FileField(
        upload_to='term_sheets/%Y/%m/',
        help_text="PDF file of the term sheet"
    )
    file_name = models.CharField(max_length=255)
    file_size_bytes = models.IntegerField()
    
    user_notes = models.TextField(
        null=True,
        blank=True,
        help_text="Optional context from the founder"
    )
    
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
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'deal_desk_termsheetanalysis'
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
        return self.red_flags.count()
    
    @property
    def scenarios_count(self):
        return self.scenarios.count()


class AnalysisRedFlag(models.Model):
    """
    Individual red flags detected in the term sheet.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        TermSheetAnalysis,
        on_delete=models.CASCADE,
        related_name='red_flags'
    )
    
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
        db_table = 'deal_desk_analysisredflag'
        ordering = ['-severity', 'created_at']
        verbose_name = 'Analysis Red Flag'
        verbose_name_plural = 'Analysis Red Flags'
    
    def __str__(self):
        return f"{self.severity}: {self.title}"


class AnalysisScenario(models.Model):
    """
    Alternative negotiation scenarios generated by AI.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(
        TermSheetAnalysis,
        on_delete=models.CASCADE,
        related_name='scenarios'
    )
    
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
        db_table = 'deal_desk_analysisscenario'
        ordering = ['scenario_label']
        verbose_name = 'Analysis Scenario'
        verbose_name_plural = 'Analysis Scenarios'
    
    def __str__(self):
        return f"{self.scenario_label}: {self.title}"
