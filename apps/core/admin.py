from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Tenant, TenantMembership, SubscriptionPlan, Subscription, TenantInvitation,
    Issuer, SecurityClass, Shareholder, Holding, Certificate, Transfer, AuditLog,
    ShareIssuanceRequest
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'status', 'primary_email', 'created_at']
    list_filter = ['status', 'country']
    search_fields = ['name', 'slug', 'primary_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Tenant Identity', {
            'fields': ('id', 'name', 'slug', 'status')
        }),
        ('Contact Information', {
            'fields': ('primary_email', 'phone', 'website')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country')
        }),
        ('Billing', {
            'fields': ('stripe_customer_id',),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'tenant', 'role', 'is_primary_contact', 'created_at']
    list_filter = ['role', 'is_primary_contact', 'tenant']
    search_fields = ['user__email', 'user__username', 'tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['tenant', 'user']


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'price_monthly', 'price_yearly', 'max_shareholders', 'is_active', 'display_order']
    list_filter = ['tier', 'is_active']
    search_fields = ['name', 'slug']
    readonly_fields = ['id', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Plan Identity', {
            'fields': ('id', 'name', 'slug', 'tier', 'description')
        }),
        ('Pricing', {
            'fields': ('price_monthly', 'price_yearly')
        }),
        ('Stripe Integration', {
            'fields': ('stripe_product_id', 'stripe_price_id_monthly', 'stripe_price_id_yearly'),
            'classes': ('collapse',)
        }),
        ('Limits', {
            'fields': ('max_shareholders', 'max_transfers_per_month', 'max_users')
        }),
        ('Features', {
            'fields': ('features',)
        }),
        ('Display', {
            'fields': ('is_active', 'display_order')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'plan', 'status', 'billing_cycle', 'current_period_end']
    list_filter = ['status', 'billing_cycle', 'plan']
    search_fields = ['tenant__name', 'stripe_subscription_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['tenant', 'plan']
    fieldsets = (
        ('Subscription Details', {
            'fields': ('id', 'tenant', 'plan', 'status', 'billing_cycle')
        }),
        ('Stripe', {
            'fields': ('stripe_subscription_id',),
            'classes': ('collapse',)
        }),
        ('Trial Period', {
            'fields': ('trial_start', 'trial_end'),
            'classes': ('collapse',)
        }),
        ('Billing Period', {
            'fields': ('current_period_start', 'current_period_end')
        }),
        ('Cancellation', {
            'fields': ('cancelled_at', 'cancel_at_period_end'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'tenant', 'role', 'status', 'expires_at', 'created_at']
    list_filter = ['status', 'role', 'tenant']
    search_fields = ['email', 'tenant__name']
    readonly_fields = ['id', 'token', 'created_at', 'accepted_at']
    autocomplete_fields = ['tenant', 'invited_by', 'accepted_by']


@admin.register(Issuer)
class IssuerAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'ticker_symbol', 'otc_tier', 'tavs_enabled', 'is_active', 'created_at']
    list_filter = ['otc_tier', 'tavs_enabled', 'is_active', 'blockchain_enabled', 'incorporation_state']
    search_fields = ['company_name', 'ticker_symbol', 'cusip', 'cik']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Company Identity', {
            'fields': ('id', 'company_name', 'ticker_symbol', 'cusip', 'cik')
        }),
        ('Incorporation Details', {
            'fields': ('incorporation_state', 'incorporation_country', 'incorporation_date')
        }),
        ('Stock Authorization', {
            'fields': ('total_authorized_shares', 'par_value')
        }),
        ('Transfer Agent Agreement', {
            'fields': ('agreement_start_date', 'agreement_end_date', 'annual_fee')
        }),
        ('OTC Markets & TAVS', {
            'fields': ('tavs_enabled', 'otc_tier', 'otc_markets_profile_url')
        }),
        ('Blockchain', {
            'fields': ('blockchain_enabled', 'blockchain_network', 'smart_contract_address'),
            'classes': ('collapse',)
        }),
        ('Contact Information', {
            'fields': ('primary_contact_name', 'primary_contact_email', 'primary_contact_phone')
        }),
        ('Metadata', {
            'fields': ('is_active', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_issuers', 'deactivate_issuers']
    
    def activate_issuers(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} issuers activated.')
    activate_issuers.short_description = 'Activate selected issuers'
    
    def deactivate_issuers(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} issuers deactivated.')
    deactivate_issuers.short_description = 'Deactivate selected issuers'


class SecurityClassInline(admin.TabularInline):
    model = SecurityClass
    extra = 0
    fields = ['security_type', 'class_designation', 'shares_authorized', 'par_value', 'voting_rights', 'is_active']


@admin.register(SecurityClass)
class SecurityClassAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'security_type', 'shares_authorized', 'voting_rights', 'is_active']
    list_filter = ['security_type', 'voting_rights', 'dividend_rights', 'is_active', 'restriction_type']
    search_fields = ['issuer__company_name', 'class_designation']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['issuer', 'converts_to']


@admin.register(Shareholder)
class ShareholderAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'account_type', 'email', 'accredited_investor', 'kyc_verified', 'is_active']
    list_filter = ['account_type', 'accredited_investor', 'kyc_verified', 'is_active', 'country']
    search_fields = ['first_name', 'last_name', 'entity_name', 'email', 'tax_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Account Information', {
            'fields': ('id', 'account_type')
        }),
        ('Personal Information (Individual)', {
            'fields': ('first_name', 'middle_name', 'last_name'),
        }),
        ('Entity Information', {
            'fields': ('entity_name', 'entity_type'),
        }),
        ('Contact Information', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country', 'email', 'phone')
        }),
        ('Tax Information (Encrypted)', {
            'fields': ('tax_id', 'tax_id_type'),
            'classes': ('collapse',)
        }),
        ('Compliance & KYC', {
            'fields': ('accredited_investor', 'accredited_date', 'kyc_verified', 'kyc_verification_date', 'kyc_provider')
        }),
        ('Blockchain', {
            'fields': ('wallet_address',),
            'classes': ('collapse',)
        }),
        ('Communication Preferences', {
            'fields': ('email_notifications', 'paper_statements')
        }),
        ('Metadata', {
            'fields': ('is_active', 'notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_accredited', 'mark_kyc_verified']
    
    def mark_accredited(self, request, queryset):
        from django.utils import timezone
        queryset.update(accredited_investor=True, accredited_date=timezone.now().date())
        self.message_user(request, f'{queryset.count()} shareholders marked as accredited.')
    mark_accredited.short_description = 'Mark as accredited investor'
    
    def mark_kyc_verified(self, request, queryset):
        from django.utils import timezone
        queryset.update(kyc_verified=True, kyc_verification_date=timezone.now().date())
        self.message_user(request, f'{queryset.count()} shareholders KYC verified.')
    mark_kyc_verified.short_description = 'Mark KYC as verified'


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ['shareholder', 'issuer', 'security_class', 'share_quantity', 'holding_type', 'is_restricted']
    list_filter = ['holding_type', 'is_restricted', 'issuer', 'security_class']
    search_fields = ['shareholder__first_name', 'shareholder__last_name', 'shareholder__entity_name', 'issuer__company_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['shareholder', 'issuer', 'security_class']


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'issuer', 'shareholder', 'shares', 'status', 'issue_date']
    list_filter = ['status', 'has_legend', 'issuer']
    search_fields = ['certificate_number', 'issuer__company_name', 'shareholder__first_name', 'shareholder__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['issuer', 'security_class', 'shareholder', 'replaces_certificate']
    
    actions = ['cancel_certificates']
    
    def cancel_certificates(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='CANCELLED', cancellation_date=timezone.now().date())
        self.message_user(request, f'{queryset.count()} certificates cancelled.')
    cancel_certificates.short_description = 'Cancel selected certificates'


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ['id', 'issuer', 'from_shareholder', 'to_shareholder', 'share_quantity', 'status', 'transfer_date']
    list_filter = ['status', 'transfer_type', 'signature_guaranteed', 'issuer']
    search_fields = ['id', 'from_shareholder__first_name', 'to_shareholder__first_name', 'issuer__company_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_by', 'processed_date']
    autocomplete_fields = ['issuer', 'security_class', 'from_shareholder', 'to_shareholder']
    date_hierarchy = 'transfer_date'
    
    fieldsets = (
        ('Transfer Details', {
            'fields': ('id', 'issuer', 'security_class', 'from_shareholder', 'to_shareholder')
        }),
        ('Share Information', {
            'fields': ('share_quantity', 'transfer_price', 'transfer_date', 'transfer_type')
        }),
        ('Status & Workflow', {
            'fields': ('status', 'rejection_reason')
        }),
        ('Validation', {
            'fields': ('signature_guaranteed', 'signature_guarantee_date', 'signature_guarantor')
        }),
        ('Certificates', {
            'fields': ('surrendered_certificates', 'new_certificates'),
            'classes': ('collapse',)
        }),
        ('Blockchain', {
            'fields': ('blockchain_hash', 'blockchain_network'),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('processed_by', 'processed_date', 'notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_transfers', 'reject_transfers', 'execute_transfers']
    
    def approve_transfers(self, request, queryset):
        from django.utils import timezone
        count = 0
        for transfer in queryset.filter(status='PENDING'):
            transfer.status = 'APPROVED'
            transfer.processed_by = request.user
            transfer.processed_date = timezone.now()
            transfer.save()
            count += 1
        self.message_user(request, f'{count} transfers approved.')
    approve_transfers.short_description = 'Approve selected transfers'
    
    def reject_transfers(self, request, queryset):
        from django.utils import timezone
        count = 0
        for transfer in queryset.filter(status='PENDING'):
            transfer.status = 'REJECTED'
            transfer.processed_by = request.user
            transfer.processed_date = timezone.now()
            transfer.save()
            count += 1
        self.message_user(request, f'{count} transfers rejected.')
    reject_transfers.short_description = 'Reject selected transfers'
    
    def execute_transfers(self, request, queryset):
        from django.db import transaction
        from django.utils import timezone
        from decimal import Decimal
        from apps.core.models import AuditLog, Holding, Certificate
        
        success_count = 0
        error_count = 0
        errors = []
        
        for transfer in queryset.filter(status='APPROVED'):
            try:
                with transaction.atomic():
                    seller_holding = Holding.objects.select_for_update().get(
                        shareholder=transfer.from_shareholder,
                        issuer=transfer.issuer,
                        security_class=transfer.security_class
                    )
                    
                    if seller_holding.share_quantity < transfer.share_quantity:
                        errors.append(f'Transfer {transfer.id}: Insufficient shares')
                        error_count += 1
                        continue
                    
                    old_seller_qty = seller_holding.share_quantity
                    seller_holding.share_quantity -= transfer.share_quantity
                    seller_holding.save()
                    
                    buyer_holding, created = Holding.objects.get_or_create(
                        shareholder=transfer.to_shareholder,
                        issuer=transfer.issuer,
                        security_class=transfer.security_class,
                        defaults={
                            'share_quantity': Decimal('0'),
                            'acquisition_date': transfer.transfer_date,
                            'holding_type': 'DRS',
                        }
                    )
                    old_buyer_qty = buyer_holding.share_quantity if not created else Decimal('0')
                    buyer_holding.share_quantity += transfer.share_quantity
                    buyer_holding.save()
                    
                    if transfer.surrendered_certificates:
                        Certificate.objects.filter(
                            issuer=transfer.issuer,
                            certificate_number__in=transfer.surrendered_certificates
                        ).update(status='CANCELLED', cancellation_date=transfer.transfer_date)
                    
                    transfer.status = 'EXECUTED'
                    transfer.processed_by = request.user
                    transfer.processed_date = timezone.now()
                    transfer.save()
                    
                    from apps.core.signals import set_audit_signal_flag, clear_audit_signal_flag
                    set_audit_signal_flag()
                    try:
                        AuditLog.objects.create(
                            user=request.user,
                            user_email=request.user.email if request.user else 'system',
                            action_type='TRANSFER_EXECUTED',
                            model_name='Transfer',
                            object_id=str(transfer.id),
                            object_repr=str(transfer),
                            new_value={
                                'transfer_id': str(transfer.id),
                                'from': str(transfer.from_shareholder),
                                'to': str(transfer.to_shareholder),
                                'shares': float(transfer.share_quantity),
                                'seller_before': float(old_seller_qty),
                                'seller_after': float(seller_holding.share_quantity),
                                'buyer_before': float(old_buyer_qty),
                                'buyer_after': float(buyer_holding.share_quantity),
                            },
                            timestamp=timezone.now(),
                            ip_address=request.META.get('REMOTE_ADDR'),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                        )
                    finally:
                        clear_audit_signal_flag()
                    
                    success_count += 1
                    
            except Holding.DoesNotExist:
                errors.append(f'Transfer {transfer.id}: Seller holding not found')
                error_count += 1
            except Exception as e:
                errors.append(f'Transfer {transfer.id}: {str(e)}')
                error_count += 1
        
        if success_count > 0:
            self.message_user(request, f'{success_count} transfers executed successfully.')
        if error_count > 0:
            self.message_user(request, f'{error_count} transfers failed: {"; ".join(errors)}', level='ERROR')
    
    execute_transfers.short_description = 'Execute selected approved transfers'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user_email', 'action_type', 'model_name', 'object_repr']
    list_filter = ['action_type', 'model_name', 'timestamp']
    search_fields = ['user_email', 'object_repr', 'object_id']
    readonly_fields = ['id', 'user', 'user_email', 'action_type', 'model_name', 'object_id', 
                      'object_repr', 'old_value', 'new_value', 'changed_fields', 'timestamp',
                      'ip_address', 'user_agent', 'request_id']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ShareIssuanceRequest)
class ShareIssuanceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'shareholder', 'issuer', 'investment_type', 'share_quantity', 
                    'price_per_share', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'investment_type', 'tenant', 'created_at']
    search_fields = ['shareholder__first_name', 'shareholder__last_name', 'shareholder__entity_name',
                     'issuer__company_name', 'stripe_checkout_session_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['shareholder', 'issuer', 'security_class', 'holding', 'requested_by']
    
    fieldsets = (
        (None, {
            'fields': ('tenant', 'shareholder', 'issuer', 'security_class', 'investment_type')
        }),
        ('Share Details', {
            'fields': ('share_quantity', 'price_per_share', 'total_amount', 'holding_type', 
                       'is_restricted', 'acquisition_type', 'cost_basis')
        }),
        ('Payment Status', {
            'fields': ('status', 'stripe_checkout_session_id', 'stripe_payment_intent_id')
        }),
        ('Result', {
            'fields': ('holding', 'send_email_notification', 'notes')
        }),
        ('Metadata', {
            'fields': ('requested_by', 'created_at', 'updated_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
