from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.utils import timezone
from pgcrypto import fields as pgcrypto_fields
import uuid


class Issuer(models.Model):
    """
    Represents a client company using our transfer agent services.
    These are the OTCID/OTCQB companies we serve.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    company_name = models.CharField(max_length=255, unique=True, help_text="Full legal company name")
    ticker_symbol = models.CharField(max_length=10, blank=True, null=True, help_text="OTC Markets ticker symbol")
    cusip = models.CharField(max_length=9, blank=True, null=True, help_text="9-character CUSIP identifier")
    cik = models.CharField(max_length=10, blank=True, null=True, help_text="SEC Central Index Key")
    
    incorporation_state = models.CharField(max_length=2)
    incorporation_country = models.CharField(max_length=2, default='US')
    incorporation_date = models.DateField(blank=True, null=True)
    
    total_authorized_shares = models.DecimalField(max_digits=20, decimal_places=0, validators=[MinValueValidator(1)])
    par_value = models.DecimalField(max_digits=10, decimal_places=4, default=0.0001)
    
    agreement_start_date = models.DateField()
    agreement_end_date = models.DateField(blank=True, null=True)
    annual_fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    OTC_TIER_CHOICES = [
        ('OTCQX', 'OTCQX Premier'),
        ('OTCQB', 'OTCQB Venture'),
        ('OTCID', 'OTCID Basic'),
        ('PINK', 'Pink Limited'),
        ('EXPERT', 'Expert Market'),
        ('NONE', 'Not Listed'),
    ]
    tavs_enabled = models.BooleanField(default=False)
    otc_tier = models.CharField(max_length=20, choices=OTC_TIER_CHOICES, default='NONE')
    otc_markets_profile_url = models.URLField(blank=True, null=True)
    
    blockchain_enabled = models.BooleanField(default=False)
    blockchain_network = models.CharField(max_length=20, blank=True, null=True)
    smart_contract_address = models.CharField(max_length=42, blank=True, null=True)
    
    primary_contact_name = models.CharField(max_length=255)
    primary_contact_email = models.EmailField()
    primary_contact_phone = models.CharField(max_length=20)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['company_name']
        indexes = [
            models.Index(fields=['ticker_symbol']),
            models.Index(fields=['cusip']),
            models.Index(fields=['otc_tier']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = "Issuer (Client Company)"
        verbose_name_plural = "Issuers (Client Companies)"
    
    def __str__(self):
        if self.ticker_symbol:
            return f"{self.company_name} ({self.ticker_symbol})"
        return self.company_name


class SecurityClass(models.Model):
    """Security class/type issued by a company."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    issuer = models.ForeignKey(Issuer, on_delete=models.CASCADE, related_name='security_classes')
    
    SECURITY_TYPE_CHOICES = [
        ('COMMON', 'Common Stock'),
        ('PREFERRED', 'Preferred Stock'),
        ('WARRANT', 'Warrant'),
        ('OPTION', 'Stock Option'),
        ('CONVERTIBLE_NOTE', 'Convertible Note'),
        ('TOKEN', 'Security Token'),
        ('NFT_SECURITY', 'NFT-Based Security'),
    ]
    security_type = models.CharField(max_length=20, choices=SECURITY_TYPE_CHOICES)
    class_designation = models.CharField(max_length=100)
    
    shares_authorized = models.DecimalField(max_digits=20, decimal_places=0, validators=[MinValueValidator(0)])
    par_value = models.DecimalField(max_digits=10, decimal_places=4, default=0.0001)
    
    voting_rights = models.BooleanField(default=True)
    votes_per_share = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    dividend_rights = models.BooleanField(default=True)
    dividend_preference = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    liquidation_preference = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    
    conversion_rights = models.BooleanField(default=False)
    converts_to = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='convertible_from')
    conversion_ratio = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    
    RESTRICTION_TYPE_CHOICES = [
        ('NONE', 'Unrestricted'),
        ('RULE_144', 'Rule 144 (1-year hold)'),
        ('RULE_701', 'Rule 701 (Employee stock)'),
        ('REG_S', 'Regulation S (Offshore)'),
        ('REG_D', 'Regulation D (Private placement)'),
        ('CUSTOM', 'Custom Restriction'),
    ]
    restriction_type = models.CharField(max_length=20, choices=RESTRICTION_TYPE_CHOICES, default='NONE')
    restriction_removal_date = models.DateField(blank=True, null=True)
    legend_text = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['issuer', 'security_type', 'class_designation']
        unique_together = ['issuer', 'security_type', 'class_designation']
        verbose_name = "Security Class"
        verbose_name_plural = "Security Classes"
    
    def __str__(self):
        return f"{self.issuer.company_name} - {self.security_type} {self.class_designation}"


class Shareholder(models.Model):
    """Beneficial owner of securities."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='shareholder')
    
    ACCOUNT_TYPE_CHOICES = [
        ('INDIVIDUAL', 'Individual'),
        ('JOINT_TENANTS', 'Joint Tenants with Rights of Survivorship'),
        ('TENANTS_COMMON', 'Tenants in Common'),
        ('ENTITY', 'Entity (Corp/LLC/Trust/Partnership)'),
        ('CUSTODIAN', 'Custodian (UTMA/UGMA)'),
        ('IRA', 'Individual Retirement Account'),
    ]
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True)
    entity_name = models.CharField(max_length=255, blank=True)
    entity_type = models.CharField(max_length=50, blank=True)
    
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=2, default='US')
    
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    TAX_ID_TYPE_CHOICES = [
        ('SSN', 'Social Security Number'),
        ('EIN', 'Employer Identification Number'),
        ('ITIN', 'Individual Taxpayer ID'),
        ('FOREIGN', 'Foreign Tax ID'),
        ('NONE', 'Not Provided'),
    ]
    tax_id = pgcrypto_fields.TextPGPSymmetricKeyField(blank=True, null=True)
    tax_id_type = models.CharField(max_length=10, choices=TAX_ID_TYPE_CHOICES, default='NONE')
    
    accredited_investor = models.BooleanField(default=False)
    accredited_date = models.DateField(blank=True, null=True)
    kyc_verified = models.BooleanField(default=False)
    kyc_verification_date = models.DateField(blank=True, null=True)
    kyc_provider = models.CharField(max_length=50, blank=True)
    
    wallet_address = models.CharField(max_length=42, blank=True, null=True)
    email_notifications = models.BooleanField(default=True)
    paper_statements = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['last_name', 'first_name', 'entity_name']
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['entity_name']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = "Shareholder"
        verbose_name_plural = "Shareholders"
    
    def __str__(self):
        if self.account_type == 'ENTITY':
            return self.entity_name or f"Entity #{self.id}"
        elif self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        else:
            return f"Shareholder #{self.id}"


class Holding(models.Model):
    """Shareholder's position in a specific security class."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    shareholder = models.ForeignKey(Shareholder, on_delete=models.PROTECT, related_name='holdings')
    issuer = models.ForeignKey(Issuer, on_delete=models.PROTECT, related_name='holdings')
    security_class = models.ForeignKey(SecurityClass, on_delete=models.PROTECT, related_name='holdings')
    
    share_quantity = models.DecimalField(max_digits=20, decimal_places=4, validators=[MinValueValidator(0)])
    acquisition_date = models.DateField()
    acquisition_price = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    cost_basis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    
    HOLDING_TYPE_CHOICES = [
        ('DRS', 'Direct Registration System (Book-Entry)'),
        ('CERTIFICATE', 'Physical Certificate'),
    ]
    holding_type = models.CharField(max_length=20, choices=HOLDING_TYPE_CHOICES, default='DRS')
    certificate_numbers = ArrayField(models.CharField(max_length=20), blank=True, null=True)
    
    is_restricted = models.BooleanField(default=False)
    restriction_type = models.CharField(max_length=50, blank=True)
    restriction_removal_date = models.DateField(blank=True, null=True)
    blockchain_token_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['issuer', 'shareholder', '-share_quantity']
        indexes = [
            models.Index(fields=['shareholder', 'issuer']),
            models.Index(fields=['issuer', 'security_class']),
            models.Index(fields=['is_restricted']),
        ]
        verbose_name = "Holding (Shareholder Position)"
        verbose_name_plural = "Holdings (Shareholder Positions)"
    
    def __str__(self):
        return f"{self.shareholder} holds {self.share_quantity} of {self.security_class}"


class Certificate(models.Model):
    """Physical stock certificate or book-entry certificate."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    issuer = models.ForeignKey(Issuer, on_delete=models.PROTECT, related_name='certificates')
    security_class = models.ForeignKey(SecurityClass, on_delete=models.PROTECT, related_name='certificates')
    shareholder = models.ForeignKey(Shareholder, on_delete=models.PROTECT, related_name='certificates')
    
    certificate_number = models.CharField(max_length=20)
    shares = models.DecimalField(max_digits=20, decimal_places=4, validators=[MinValueValidator(0)])
    
    STATUS_CHOICES = [
        ('OUTSTANDING', 'Outstanding (Active)'),
        ('CANCELLED', 'Cancelled (Surrendered for transfer)'),
        ('REPLACED', 'Replaced (Lost/Damaged)'),
        ('LOST', 'Lost/Stolen'),
        ('ESCROW', 'Held in Escrow'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OUTSTANDING')
    
    issue_date = models.DateField()
    cancellation_date = models.DateField(blank=True, null=True)
    has_legend = models.BooleanField(default=False)
    legend_text = models.TextField(blank=True)
    replaces_certificate = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='replaced_by')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['issuer', 'certificate_number']
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['issuer', 'certificate_number']),
            models.Index(fields=['shareholder', 'status']),
            models.Index(fields=['status']),
        ]
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"
    
    def __str__(self):
        return f"Cert #{self.certificate_number} - {self.issuer.ticker_symbol or self.issuer.company_name}"


class Transfer(models.Model):
    """Transfer of shares from one shareholder to another."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    issuer = models.ForeignKey(Issuer, on_delete=models.PROTECT, related_name='transfers')
    security_class = models.ForeignKey(SecurityClass, on_delete=models.PROTECT, related_name='transfers')
    from_shareholder = models.ForeignKey(Shareholder, on_delete=models.PROTECT, related_name='transfers_out')
    to_shareholder = models.ForeignKey(Shareholder, on_delete=models.PROTECT, related_name='transfers_in')
    
    share_quantity = models.DecimalField(max_digits=20, decimal_places=4, validators=[MinValueValidator(0.0001)])
    transfer_price = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True)
    transfer_date = models.DateField()
    
    TRANSFER_TYPE_CHOICES = [
        ('SALE', 'Sale (Taxable)'),
        ('GIFT', 'Gift (Non-taxable)'),
        ('INHERITANCE', 'Inheritance'),
        ('DIVORCE', 'Divorce Settlement'),
        ('CORPORATE_ACTION', 'Corporate Action (Dividend, Split, etc.)'),
        ('CONVERSION', 'Conversion (Preferred → Common)'),
        ('EXERCISE', 'Option/Warrant Exercise'),
        ('OTHER', 'Other'),
    ]
    transfer_type = models.CharField(max_length=20, choices=TRANSFER_TYPE_CHOICES, default='SALE')
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending (Awaiting Documents)'),
        ('VALIDATING', 'Under Review'),
        ('APPROVED', 'Approved (Ready to Execute)'),
        ('EXECUTED', 'Executed (Completed)'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    signature_guaranteed = models.BooleanField(default=False)
    signature_guarantee_date = models.DateField(blank=True, null=True)
    signature_guarantor = models.CharField(max_length=255, blank=True)
    
    surrendered_certificates = ArrayField(models.CharField(max_length=20), blank=True, null=True)
    new_certificates = ArrayField(models.CharField(max_length=20), blank=True, null=True)
    
    blockchain_hash = models.CharField(max_length=66, blank=True, null=True)
    blockchain_network = models.CharField(max_length=20, blank=True, null=True)
    
    processed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, blank=True, null=True, related_name='transfers_processed')
    processed_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-transfer_date', '-created_at']
        indexes = [
            models.Index(fields=['issuer', 'status']),
            models.Index(fields=['from_shareholder']),
            models.Index(fields=['to_shareholder']),
            models.Index(fields=['status']),
            models.Index(fields=['transfer_date']),
        ]
        verbose_name = "Transfer"
        verbose_name_plural = "Transfers"
    
    def __str__(self):
        return f"Transfer #{self.id}: {self.from_shareholder} → {self.to_shareholder} ({self.share_quantity} shares)"


class AuditLog(models.Model):
    """Immutable audit trail for all database changes."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    user_email = models.CharField(max_length=255)
    
    ACTION_TYPE_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted (Soft)'),
        ('TRANSFER_EXECUTED', 'Transfer Executed'),
        ('CERTIFICATE_ISSUED', 'Certificate Issued'),
        ('CERTIFICATE_CANCELLED', 'Certificate Cancelled'),
        ('TAVS_SUBMITTED', 'TAVS Report Submitted'),
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('EXPORT', 'Data Exported'),
    ]
    action_type = models.CharField(max_length=30, choices=ACTION_TYPE_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.CharField(max_length=36)
    object_repr = models.CharField(max_length=255)
    
    old_value = models.JSONField(blank=True, null=True)
    new_value = models.JSONField(blank=True, null=True)
    changed_fields = ArrayField(models.CharField(max_length=100), blank=True, null=True)
    
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    request_id = models.UUIDField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['user']),
            models.Index(fields=['action_type']),
        ]
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log"
    
    def save(self, *args, **kwargs):
        """Enforce append-only: cannot update existing records"""
        if self.pk is not None:
            raise ValueError("AuditLog records are immutable and cannot be updated")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of audit logs"""
        raise ValueError("AuditLog records cannot be deleted (SEC compliance)")
    
    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} - {self.user_email} - {self.action_type} - {self.model_name}"
