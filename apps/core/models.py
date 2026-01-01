from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from pgcrypto import fields as pgcrypto_fields
import uuid


# ==============================================================================
# MULTI-TENANT MODELS
# ==============================================================================

class Tenant(models.Model):
    """
    Represents a company/organization using the platform.
    Each pre-seed OTCID company is a separate tenant with isolated data.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=255, help_text="Company/organization name")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly identifier")
    
    primary_email = models.EmailField(help_text="Primary contact email")
    phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, default='US')
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Activation'),
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Customer ID")
    
    settings = models.JSONField(default=dict, blank=True, help_text="Tenant-specific settings")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['stripe_customer_id']),
        ]
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
    
    def __str__(self):
        return self.name


class TenantMembership(models.Model):
    """
    Links users to tenants with specific roles.
    A user can belong to multiple tenants with different roles.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='tenant_memberships')
    
    ROLE_CHOICES = [
        ('PLATFORM_ADMIN', 'Platform Administrator'),  # Tableicty staff - can access all tenants
        ('TENANT_ADMIN', 'Tenant Administrator'),      # Company admin - full access to their tenant
        ('TENANT_STAFF', 'Tenant Staff'),              # Company staff - limited admin access
        ('SHAREHOLDER', 'Shareholder'),                # Shareholder - view-only access to their holdings
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='SHAREHOLDER')
    
    is_primary_contact = models.BooleanField(default=False, help_text="Primary contact for the tenant")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tenant', 'user']
        ordering = ['tenant', 'role', 'user']
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['tenant', 'role']),
        ]
        verbose_name = "Tenant Membership"
        verbose_name_plural = "Tenant Memberships"
    
    def __str__(self):
        return f"{self.user.email} - {self.tenant.name} ({self.get_role_display()})"


class SubscriptionPlan(models.Model):
    """
    Defines the available subscription tiers.
    Three tiers: Starter (self-service), Growth (managed), Enterprise (DTCC-ready)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    TIER_CHOICES = [
        ('STARTER', 'Starter'),      # Self-service cap table management
        ('PROFESSIONAL', 'Professional'),  # + Transfer processing, compliance reports
        ('ENTERPRISE', 'Enterprise'), # + Full TA services, DTCC integration
    ]
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, help_text="Annual price (usually discounted)")
    
    stripe_price_id_monthly = models.CharField(max_length=255, blank=True, null=True)
    stripe_price_id_yearly = models.CharField(max_length=255, blank=True, null=True)
    stripe_product_id = models.CharField(max_length=255, blank=True, null=True)
    
    max_shareholders = models.IntegerField(default=100, help_text="Maximum shareholders allowed")
    max_transfers_per_month = models.IntegerField(default=10, help_text="Maximum transfers per month")
    max_users = models.IntegerField(default=3, help_text="Maximum admin users")
    
    features = models.JSONField(default=list, blank=True, help_text="List of feature flags enabled")
    
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'price_monthly']
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"
    
    def __str__(self):
        return f"{self.name} (${self.price_monthly}/mo)"


class Subscription(models.Model):
    """
    Active subscription for a tenant.
    Tracks billing status and feature access.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant = models.OneToOneField(Tenant, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    
    STATUS_CHOICES = [
        ('TRIALING', 'Trial Period'),
        ('ACTIVE', 'Active'),
        ('PAST_DUE', 'Past Due'),
        ('CANCELLED', 'Cancelled'),
        ('PAUSED', 'Paused'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TRIALING')
    
    BILLING_CYCLE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='MONTHLY')
    
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    trial_start = models.DateTimeField(blank=True, null=True)
    trial_end = models.DateTimeField(blank=True, null=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    
    cancelled_at = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['stripe_subscription_id']),
        ]
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
    
    def __str__(self):
        return f"{self.tenant.name} - {self.plan.name} ({self.status})"


class TenantInvitation(models.Model):
    """
    Invitation for a user to join a tenant.
    Used for onboarding new shareholders and staff.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='sent_invitations')
    
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=TenantMembership.ROLE_CHOICES, default='SHAREHOLDER')
    
    token = models.CharField(max_length=100, unique=True)
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('EXPIRED', 'Expired'),
        ('REVOKED', 'Revoked'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(blank=True, null=True)
    accepted_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_invitations')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['email', 'status']),
            models.Index(fields=['tenant', 'status']),
        ]
        verbose_name = "Tenant Invitation"
        verbose_name_plural = "Tenant Invitations"
    
    def __str__(self):
        return f"Invite to {self.tenant.name} for {self.email}"
    
    def is_valid(self):
        return self.status == 'PENDING' and self.expires_at > timezone.now()


# ==============================================================================
# TRANSFER AGENT MODELS
# ==============================================================================

class Issuer(models.Model):
    """
    Represents a client company using our transfer agent services.
    These are the OTCID/OTCQB companies we serve.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='issuers',
        null=True,  # Nullable for migration - will be required after backfill
        blank=True,
        help_text="Tenant this issuer belongs to"
    )
    
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
    
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='shareholders',
        null=True,  # Nullable for migration - will be required after backfill
        blank=True,
        help_text="Tenant this shareholder belongs to"
    )
    
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
    
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='holdings',
        null=True,  # Nullable for migration - will be required after backfill
        blank=True,
        help_text="Tenant this holding belongs to"
    )
    
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
    
    HOLDING_STATUS_CHOICES = [
        ('HELD', 'Held (Pending Release)'),
        ('ACTIVE', 'Active (Released)'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20, 
        choices=HOLDING_STATUS_CHOICES, 
        default='ACTIVE',
        help_text="HELD = in holding bucket, ACTIVE = released to shareholder"
    )
    held_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When shares were placed in holding bucket"
    )
    released_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When shares were released from holding bucket"
    )
    released_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='released_holdings',
        help_text="Admin who released the shares"
    )
    share_issuance_request = models.ForeignKey(
        'ShareIssuanceRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='holdings',
        help_text="Link to the issuance request (for payment tracking)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['issuer', 'shareholder', '-share_quantity']
        indexes = [
            models.Index(fields=['shareholder', 'issuer']),
            models.Index(fields=['issuer', 'security_class']),
            models.Index(fields=['is_restricted']),
            models.Index(fields=['status']),
        ]
        verbose_name = "Holding (Shareholder Position)"
        verbose_name_plural = "Holdings (Shareholder Positions)"
    
    def __str__(self):
        status_indicator = " [HELD]" if self.status == 'HELD' else ""
        return f"{self.shareholder} holds {self.share_quantity} of {self.security_class}{status_indicator}"


class Certificate(models.Model):
    """Physical stock certificate or book-entry certificate."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='certificates',
        null=True,  # Nullable for migration - will be required after backfill
        blank=True,
        help_text="Tenant this certificate belongs to"
    )
    
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
    
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.CASCADE, 
        related_name='transfers',
        null=True,  # Nullable for migration - will be required after backfill
        blank=True,
        help_text="Tenant this transfer belongs to"
    )
    
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
    
    tenant = models.ForeignKey(
        Tenant, 
        on_delete=models.SET_NULL,  # Don't cascade delete audit logs 
        related_name='audit_logs',
        null=True,  # Nullable - some audit logs may be system-level
        blank=True,
        help_text="Tenant this audit log belongs to (null for system-level logs)"
    )
    
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
        """
        AuditLog entries are immutable and can only be created via Django signals.
        Direct creates are blocked for security.
        """
        from apps.core.signals import is_from_signal  # Import here to avoid circular import
        
        # Block updates to existing entries
        if not self._state.adding:
            raise ValidationError(
                "AuditLog entries cannot be modified after creation. "
                "Audit trail must remain immutable for compliance."
            )
        
        # Block direct creates (must come from signals)
        if not is_from_signal():
            raise ValidationError(
                "AuditLog entries can only be created automatically via Django signals. "
                "Do not create AuditLog entries directly using AuditLog.objects.create(). "
                "All audit logging happens automatically when models are saved."
            )
        
        # If we get here, it's a legitimate signal-driven create
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """AuditLog entries cannot be deleted"""
        raise ValidationError(
            "AuditLog entries cannot be deleted. "
            "Audit trail must remain intact for compliance."
        )
    
    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} - {self.user_email} - {self.action_type} - {self.model_name}"


class ShareIssuanceRequest(models.Model):
    """
    Tracks share issuance requests, especially for payment-required investment types.
    Shares are only issued after payment confirmation for retail/friends & family investments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='share_issuance_requests',
        help_text="Tenant this issuance request belongs to"
    )
    
    shareholder = models.ForeignKey(
        Shareholder,
        on_delete=models.CASCADE,
        related_name='issuance_requests',
        help_text="Shareholder receiving shares"
    )
    issuer = models.ForeignKey(
        Issuer,
        on_delete=models.CASCADE,
        related_name='issuance_requests',
        help_text="Issuer of the shares"
    )
    security_class = models.ForeignKey(
        SecurityClass,
        on_delete=models.CASCADE,
        related_name='issuance_requests',
        help_text="Security class being issued"
    )
    
    INVESTMENT_TYPE_CHOICES = [
        ('FOUNDER_SHARES', 'Founder Shares'),
        ('SEED_ROUND', 'Seed Round Funding'),
        ('RETAIL', 'Retail Investment'),
        ('FRIENDS_FAMILY', 'Friends & Family'),
    ]
    investment_type = models.CharField(
        max_length=20,
        choices=INVESTMENT_TYPE_CHOICES,
        help_text="Type of investment - determines if payment is required"
    )
    
    share_quantity = models.DecimalField(
        max_digits=20,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        help_text="Number of shares to issue"
    )
    price_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        help_text="Price per share"
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total payment amount (shares * price)"
    )
    
    STATUS_CHOICES = [
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('PAYMENT_PROCESSING', 'Payment Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING_PAYMENT',
        help_text="Current status of the issuance request"
    )
    
    stripe_checkout_session_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Checkout Session ID for payment"
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Payment Intent ID"
    )
    
    holding = models.ForeignKey(
        Holding,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='issuance_request',
        help_text="The holding created after successful payment"
    )
    
    holding_type = models.CharField(max_length=20, default='DRS')
    is_restricted = models.BooleanField(default=False)
    acquisition_type = models.CharField(max_length=20, default='ISSUANCE')
    cost_basis = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True)
    
    send_email_notification = models.BooleanField(
        default=True,
        help_text="Whether to send email notification after issuance"
    )
    
    requested_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='share_issuance_requests',
        help_text="Admin user who initiated the request"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['shareholder', 'status']),
            models.Index(fields=['stripe_checkout_session_id']),
            models.Index(fields=['status', 'expires_at']),
        ]
        verbose_name = "Share Issuance Request"
        verbose_name_plural = "Share Issuance Requests"
    
    def __str__(self):
        return f"{self.shareholder} - {self.share_quantity} shares ({self.get_status_display()})"
    
    @property
    def requires_payment(self) -> bool:
        """Returns True if this investment type requires payment."""
        return self.investment_type in ('RETAIL', 'FRIENDS_FAMILY')
    
    def save(self, *args, **kwargs):
        if not self.total_amount:
            self.total_amount = self.share_quantity * self.price_per_share
        super().save(*args, **kwargs)
