"""
Management command to create the default tenant and backfill existing data.

This command should be run once after applying the multi-tenancy migrations
to ensure all existing data is associated with a default tenant.

Usage:
    python manage.py setup_default_tenant
    python manage.py setup_default_tenant --tenant-name "My Company" --tenant-slug "my-company"
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import (
    Tenant, TenantMembership, SubscriptionPlan, Subscription,
    Issuer, Shareholder, Holding, Certificate, Transfer, AuditLog
)
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create default tenant and backfill existing data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant-name',
            default='Tableicty (Platform Owner)',
            help='Name for the default tenant'
        )
        parser.add_argument(
            '--tenant-slug',
            default='tableicty',
            help='URL slug for the default tenant'
        )
        parser.add_argument(
            '--email',
            default='admin@tableicty.com',
            help='Primary email for the default tenant'
        )

    def handle(self, *args, **options):
        tenant_name = options['tenant_name']
        tenant_slug = options['tenant_slug']
        email = options['email']

        self.stdout.write(self.style.NOTICE(f'Setting up default tenant: {tenant_name}'))

        with transaction.atomic():
            tenant, created = Tenant.objects.get_or_create(
                slug=tenant_slug,
                defaults={
                    'name': tenant_name,
                    'primary_email': email,
                    'status': 'ACTIVE',
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created tenant: {tenant.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Tenant already exists: {tenant.name}'))

            self._create_subscription_plans()

            starter_plan = SubscriptionPlan.objects.filter(tier='STARTER').first()
            if starter_plan:
                subscription, sub_created = Subscription.objects.get_or_create(
                    tenant=tenant,
                    defaults={
                        'plan': starter_plan,
                        'status': 'ACTIVE',
                        'billing_cycle': 'MONTHLY',
                    }
                )
                if sub_created:
                    self.stdout.write(self.style.SUCCESS(f'Created subscription: {subscription}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Subscription already exists'))

            self._backfill_tenant_data(tenant)

            self._assign_admin_memberships(tenant)

        self.stdout.write(self.style.SUCCESS('Default tenant setup complete!'))

    def _create_subscription_plans(self):
        """Create the three subscription tiers if they don't exist."""
        plans = [
            {
                'name': 'Starter',
                'slug': 'starter',
                'tier': 'STARTER',
                'description': 'Self-service cap table management for early-stage companies',
                'price_monthly': 49.00,
                'price_yearly': 490.00,
                'max_shareholders': 50,
                'max_transfers_per_month': 5,
                'max_users': 2,
                'display_order': 1,
                'features': ['cap_table', 'shareholder_portal', 'basic_reports'],
            },
            {
                'name': 'Growth',
                'slug': 'growth',
                'tier': 'GROWTH',
                'description': 'Managed cap table with transfer processing and compliance',
                'price_monthly': 199.00,
                'price_yearly': 1990.00,
                'max_shareholders': 250,
                'max_transfers_per_month': 25,
                'max_users': 5,
                'display_order': 2,
                'features': ['cap_table', 'shareholder_portal', 'basic_reports', 'transfer_processing', 'compliance_reports', 'email_notifications'],
            },
            {
                'name': 'Enterprise',
                'slug': 'enterprise',
                'tier': 'ENTERPRISE',
                'description': 'Full transfer agent services with DTCC integration readiness',
                'price_monthly': 499.00,
                'price_yearly': 4990.00,
                'max_shareholders': 9999,
                'max_transfers_per_month': 999,
                'max_users': 20,
                'display_order': 3,
                'features': ['cap_table', 'shareholder_portal', 'basic_reports', 'transfer_processing', 'compliance_reports', 'email_notifications', 'tavs_integration', 'dtcc_ready', 'api_access', 'custom_branding'],
            },
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                tier=plan_data['tier'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created plan: {plan.name}'))
            else:
                self.stdout.write(f'  Plan exists: {plan.name}')

    def _backfill_tenant_data(self, tenant):
        """Associate all existing data with the default tenant."""
        models_to_backfill = [
            (Issuer, 'issuers'),
            (Shareholder, 'shareholders'),
            (Holding, 'holdings'),
            (Certificate, 'certificates'),
            (Transfer, 'transfers'),
        ]

        for model, name in models_to_backfill:
            count = model.objects.filter(tenant__isnull=True).update(tenant=tenant)
            if count > 0:
                self.stdout.write(self.style.SUCCESS(f'  Backfilled {count} {name}'))
            else:
                self.stdout.write(f'  No {name} to backfill')

        audit_count = AuditLog.objects.filter(tenant__isnull=True).update(tenant=tenant)
        if audit_count > 0:
            self.stdout.write(self.style.SUCCESS(f'  Backfilled {audit_count} audit logs'))

    def _assign_admin_memberships(self, tenant):
        """Create tenant memberships for existing admin users."""
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        
        for user in admin_users:
            membership, created = TenantMembership.objects.get_or_create(
                tenant=tenant,
                user=user,
                defaults={
                    'role': 'PLATFORM_ADMIN',
                    'is_primary_contact': user.is_superuser,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Added {user.email} as Platform Admin'))

        shareholders = Shareholder.objects.filter(
            user__isnull=False,
            tenant=tenant
        ).select_related('user')
        
        for shareholder in shareholders:
            if shareholder.user:
                membership, created = TenantMembership.objects.get_or_create(
                    tenant=tenant,
                    user=shareholder.user,
                    defaults={
                        'role': 'SHAREHOLDER',
                    }
                )
                if created:
                    self.stdout.write(f'  Added {shareholder.user.email} as Shareholder member')
