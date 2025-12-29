"""
Management command to seed subscription plans.
Run with: python manage.py seed_subscription_plans
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.core.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed subscription plans (Starter, Professional, Enterprise)'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Starter',
                'slug': 'starter',
                'tier': 'STARTER',
                'description': 'Basic cap table management for small companies',
                'price_monthly': Decimal('199.00'),
                'price_yearly': Decimal('1990.00'),
                'max_shareholders': 25,
                'max_transfers_per_month': 10,
                'max_users': 1,
                'features': [
                    'cap_table_management',
                    'shareholder_registry',
                    'basic_reporting',
                ],
                'display_order': 1,
                'is_active': True,
            },
            {
                'name': 'Professional',
                'slug': 'professional',
                'tier': 'GROWTH',
                'description': 'Full-featured transfer agent for growing companies',
                'price_monthly': Decimal('499.00'),
                'price_yearly': Decimal('4990.00'),
                'max_shareholders': 200,
                'max_transfers_per_month': 100,
                'max_users': 3,
                'features': [
                    'cap_table_management',
                    'shareholder_registry',
                    'basic_reporting',
                    'email_invitations',
                    'transfer_processing',
                    'compliance_reports',
                ],
                'display_order': 2,
                'is_active': True,
            },
            {
                'name': 'Enterprise',
                'slug': 'enterprise',
                'tier': 'ENTERPRISE',
                'description': 'Unlimited access with DTCC integration for public companies',
                'price_monthly': Decimal('1499.00'),
                'price_yearly': Decimal('14990.00'),
                'max_shareholders': -1,
                'max_transfers_per_month': -1,
                'max_users': -1,
                'features': [
                    'cap_table_management',
                    'shareholder_registry',
                    'basic_reporting',
                    'email_invitations',
                    'transfer_processing',
                    'compliance_reports',
                    'certificate_management',
                    'dtcc_integration',
                    'priority_support',
                    'custom_branding',
                    'api_access',
                ],
                'display_order': 3,
                'is_active': True,
            }
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.update_or_create(
                tier=plan_data['tier'],
                defaults=plan_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Updated plan: {plan.name}"))

        total = SubscriptionPlan.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created_count}, Updated: {updated_count}, Total plans: {total}"
        ))
        
        self.stdout.write("\nPlan Summary:")
        for plan in SubscriptionPlan.objects.all().order_by('display_order'):
            limit_display = "unlimited" if plan.max_shareholders == -1 else str(plan.max_shareholders)
            self.stdout.write(
                f"  - {plan.name}: ${plan.price_monthly}/mo, "
                f"{limit_display} shareholders, {plan.max_users} admins"
            )
