"""
Management command to seed subscription plans.
Run with: python manage.py seed_subscription_plans
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.core.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed subscription plans (Starter, Growth, Enterprise)'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Starter',
                'tier': 'STARTER',
                'price_monthly': Decimal('49.00'),
                'price_yearly': Decimal('490.00'),
                'max_shareholders': 100,
                'max_transfers_per_month': 50,
                'max_users': 3,
                'is_active': True,
            },
            {
                'name': 'Growth',
                'tier': 'GROWTH',
                'price_monthly': Decimal('199.00'),
                'price_yearly': Decimal('1990.00'),
                'max_shareholders': 500,
                'max_transfers_per_month': 200,
                'max_users': 10,
                'is_active': True,
            },
            {
                'name': 'Enterprise',
                'tier': 'ENTERPRISE',
                'price_monthly': Decimal('499.00'),
                'price_yearly': Decimal('4990.00'),
                'max_shareholders': -1,
                'max_transfers_per_month': -1,
                'max_users': -1,
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
