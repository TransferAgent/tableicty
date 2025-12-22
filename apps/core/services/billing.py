"""
Billing service for Stripe integration.

Handles Customer creation, Subscription management, and Checkout sessions.
"""
import logging
from typing import Optional
from django.conf import settings
from django.db import transaction

from apps.core.models import Tenant, Subscription, SubscriptionPlan
from apps.core.stripe import get_stripe_client, is_stripe_configured

logger = logging.getLogger(__name__)


class BillingService:
    """Service class for Stripe billing operations."""
    
    def __init__(self):
        self._stripe = None
    
    @property
    def stripe(self):
        if self._stripe is None:
            self._stripe = get_stripe_client()
        return self._stripe
    
    def get_or_create_customer(self, tenant: Tenant) -> str:
        """
        Get existing Stripe customer or create a new one for the tenant.
        
        Returns the Stripe customer ID.
        """
        if tenant.stripe_customer_id:
            return tenant.stripe_customer_id
        
        customer = self.stripe.Customer.create(
            name=tenant.name,
            email=tenant.primary_email,
            metadata={
                'tenant_id': str(tenant.id),
                'tenant_slug': tenant.slug,
            }
        )
        
        tenant.stripe_customer_id = customer.id
        tenant.save(update_fields=['stripe_customer_id'])
        
        logger.info(f"Created Stripe customer {customer.id} for tenant {tenant.id}")
        return customer.id
    
    def create_checkout_session(
        self,
        tenant: Tenant,
        plan: SubscriptionPlan,
        billing_cycle: str = 'monthly',
        success_url: str = '',
        cancel_url: str = '',
    ) -> dict:
        """
        Create a Stripe Checkout session for subscription.
        
        Args:
            tenant: The tenant subscribing
            plan: The subscription plan
            billing_cycle: 'monthly' or 'yearly'
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            
        Returns:
            Dict with 'session_id' and 'url'
        """
        customer_id = self.get_or_create_customer(tenant)
        
        price_id = (
            plan.stripe_price_id_yearly if billing_cycle == 'yearly'
            else plan.stripe_price_id_monthly
        )
        
        if not price_id:
            raise ValueError(f"Plan {plan.name} does not have a Stripe price ID for {billing_cycle} billing")
        
        session = self.stripe.checkout.Session.create(
            customer=customer_id,
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            success_url=success_url or f"{settings.FRONTEND_URL}/dashboard/billing?success=true",
            cancel_url=cancel_url or f"{settings.FRONTEND_URL}/dashboard/billing?canceled=true",
            metadata={
                'tenant_id': str(tenant.id),
                'plan_id': str(plan.id),
                'billing_cycle': billing_cycle,
            },
            subscription_data={
                'metadata': {
                    'tenant_id': str(tenant.id),
                    'plan_id': str(plan.id),
                }
            }
        )
        
        logger.info(f"Created checkout session {session.id} for tenant {tenant.id}")
        return {
            'session_id': session.id,
            'url': session.url,
        }
    
    def create_billing_portal_session(self, tenant: Tenant, return_url: str = '') -> dict:
        """
        Create a Stripe Billing Portal session for managing subscription.
        
        Returns:
            Dict with 'url'
        """
        customer_id = self.get_or_create_customer(tenant)
        
        session = self.stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url or f"{settings.FRONTEND_URL}/dashboard/billing",
        )
        
        return {'url': session.url}
    
    @transaction.atomic
    def sync_subscription_from_stripe(
        self,
        tenant: Tenant,
        stripe_subscription_id: str,
        stripe_data: dict,
    ) -> Subscription:
        """
        Sync subscription data from Stripe to the database.
        
        Called by webhook handlers.
        """
        from datetime import datetime
        
        subscription = Subscription.objects.filter(
            tenant=tenant
        ).first()
        
        status_mapping = {
            'active': 'ACTIVE',
            'trialing': 'TRIALING',
            'past_due': 'PAST_DUE',
            'canceled': 'CANCELED',
            'unpaid': 'PAST_DUE',
            'incomplete': 'PENDING',
            'incomplete_expired': 'CANCELED',
        }
        
        stripe_status = stripe_data.get('status', 'active')
        mapped_status = status_mapping.get(stripe_status, 'ACTIVE')
        
        current_period_start = None
        current_period_end = None
        if stripe_data.get('current_period_start'):
            current_period_start = datetime.fromtimestamp(stripe_data['current_period_start'])
        if stripe_data.get('current_period_end'):
            current_period_end = datetime.fromtimestamp(stripe_data['current_period_end'])
        
        plan_id = stripe_data.get('metadata', {}).get('plan_id')
        plan = None
        if plan_id:
            try:
                plan = SubscriptionPlan.objects.get(id=plan_id)
            except SubscriptionPlan.DoesNotExist:
                pass
        
        if subscription:
            subscription.stripe_subscription_id = stripe_subscription_id
            subscription.status = mapped_status
            if plan:
                subscription.plan = plan
            if current_period_start:
                subscription.current_period_start = current_period_start
            if current_period_end:
                subscription.current_period_end = current_period_end
            subscription.save()
        else:
            if not plan:
                plan = SubscriptionPlan.objects.filter(tier='STARTER').first()
            
            subscription = Subscription.objects.create(
                tenant=tenant,
                plan=plan,
                status=mapped_status,
                stripe_subscription_id=stripe_subscription_id,
                stripe_customer_id=tenant.stripe_customer_id,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
            )
        
        logger.info(f"Synced subscription {stripe_subscription_id} for tenant {tenant.id}")
        return subscription
    
    def cancel_subscription(self, tenant: Tenant, at_period_end: bool = True) -> dict:
        """
        Cancel the tenant's subscription.
        
        Args:
            tenant: The tenant
            at_period_end: If True, cancel at end of billing period
            
        Returns:
            Dict with cancellation status
        """
        subscription = Subscription.objects.filter(
            tenant=tenant,
            stripe_subscription_id__isnull=False,
        ).first()
        
        if not subscription or not subscription.stripe_subscription_id:
            raise ValueError("No active subscription found")
        
        if at_period_end:
            self.stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            subscription.status = 'CANCELED'
        else:
            self.stripe.Subscription.cancel(subscription.stripe_subscription_id)
            subscription.status = 'CANCELED'
        
        subscription.save(update_fields=['status'])
        
        logger.info(f"Canceled subscription for tenant {tenant.id}")
        return {'status': 'canceled', 'at_period_end': at_period_end}


billing_service = BillingService()
