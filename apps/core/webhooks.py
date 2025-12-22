"""
Stripe webhook handlers.

Handles subscription lifecycle events from Stripe.
"""
import logging
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.models import Tenant, Subscription, SubscriptionPlan
from apps.core.stripe import get_stripe_client

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    
    Events handled:
    - checkout.session.completed
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_failed
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured")
        return HttpResponse(status=400)
    
    try:
        stripe = get_stripe_client()
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)
    
    event_type = event['type']
    data = event['data']['object']
    
    logger.info(f"Received Stripe webhook: {event_type}")
    
    try:
        if event_type == 'checkout.session.completed':
            handle_checkout_completed(data)
        elif event_type == 'customer.subscription.created':
            handle_subscription_created(data)
        elif event_type == 'customer.subscription.updated':
            handle_subscription_updated(data)
        elif event_type == 'customer.subscription.deleted':
            handle_subscription_deleted(data)
        elif event_type == 'invoice.payment_failed':
            handle_payment_failed(data)
        else:
            logger.info(f"Unhandled event type: {event_type}")
    except Exception as e:
        logger.exception(f"Error handling webhook {event_type}: {e}")
        return HttpResponse(status=500)
    
    return HttpResponse(status=200)


def handle_checkout_completed(session):
    """Handle successful checkout session completion."""
    tenant_id = session.get('metadata', {}).get('tenant_id')
    plan_id = session.get('metadata', {}).get('plan_id')
    billing_cycle = session.get('metadata', {}).get('billing_cycle', 'monthly')
    subscription_id = session.get('subscription')
    customer_id = session.get('customer')
    
    if not tenant_id:
        logger.error("Checkout session missing tenant_id in metadata")
        return
    
    try:
        tenant = Tenant.objects.get(id=tenant_id)
    except Tenant.DoesNotExist:
        logger.error(f"Tenant {tenant_id} not found")
        return
    
    if customer_id and not tenant.stripe_customer_id:
        tenant.stripe_customer_id = customer_id
        tenant.save(update_fields=['stripe_customer_id'])
    
    if subscription_id and plan_id:
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            logger.error(f"Plan {plan_id} not found")
            return
        
        subscription = Subscription.objects.filter(tenant=tenant).first()
        if subscription:
            subscription.plan = plan
            subscription.billing_cycle = billing_cycle.upper()
            subscription.status = 'ACTIVE'
            subscription.stripe_subscription_id = subscription_id
            subscription.stripe_customer_id = customer_id
            subscription.save()
        else:
            Subscription.objects.create(
                tenant=tenant,
                plan=plan,
                billing_cycle=billing_cycle.upper(),
                status='ACTIVE',
                stripe_subscription_id=subscription_id,
                stripe_customer_id=customer_id,
            )
    
    logger.info(f"Checkout completed for tenant {tenant_id}")


def handle_subscription_created(subscription_data):
    """Handle subscription creation."""
    customer_id = subscription_data.get('customer')
    subscription_id = subscription_data.get('id')
    status = subscription_data.get('status')
    
    tenant = Tenant.objects.filter(stripe_customer_id=customer_id).first()
    if not tenant:
        logger.warning(f"No tenant found for customer {customer_id}")
        return
    
    status_mapping = {
        'active': 'ACTIVE',
        'trialing': 'TRIALING',
        'past_due': 'PAST_DUE',
        'canceled': 'CANCELED',
        'unpaid': 'PAST_DUE',
    }
    
    subscription = Subscription.objects.filter(tenant=tenant).first()
    if subscription:
        subscription.stripe_subscription_id = subscription_id
        subscription.status = status_mapping.get(status, 'ACTIVE')
        update_subscription_period(subscription, subscription_data)
        subscription.save()
    
    logger.info(f"Subscription created for tenant {tenant.id}")


def handle_subscription_updated(subscription_data):
    """Handle subscription updates."""
    subscription_id = subscription_data.get('id')
    status = subscription_data.get('status')
    cancel_at_period_end = subscription_data.get('cancel_at_period_end', False)
    
    subscription = Subscription.objects.filter(
        stripe_subscription_id=subscription_id
    ).first()
    
    if not subscription:
        logger.warning(f"Subscription {subscription_id} not found")
        return
    
    status_mapping = {
        'active': 'ACTIVE',
        'trialing': 'TRIALING',
        'past_due': 'PAST_DUE',
        'canceled': 'CANCELED',
        'unpaid': 'PAST_DUE',
    }
    
    subscription.status = status_mapping.get(status, subscription.status)
    update_subscription_period(subscription, subscription_data)
    
    if cancel_at_period_end:
        subscription.status = 'CANCELED'
    
    subscription.save()
    logger.info(f"Subscription {subscription_id} updated")


def handle_subscription_deleted(subscription_data):
    """Handle subscription cancellation."""
    subscription_id = subscription_data.get('id')
    
    subscription = Subscription.objects.filter(
        stripe_subscription_id=subscription_id
    ).first()
    
    if subscription:
        subscription.status = 'CANCELED'
        subscription.save(update_fields=['status'])
        logger.info(f"Subscription {subscription_id} canceled")


def handle_payment_failed(invoice_data):
    """Handle failed payment."""
    customer_id = invoice_data.get('customer')
    subscription_id = invoice_data.get('subscription')
    
    subscription = Subscription.objects.filter(
        stripe_subscription_id=subscription_id
    ).first()
    
    if subscription:
        subscription.status = 'PAST_DUE'
        subscription.save(update_fields=['status'])
        logger.warning(f"Payment failed for subscription {subscription_id}")


def update_subscription_period(subscription, stripe_data):
    """Update subscription period dates from Stripe data."""
    if stripe_data.get('current_period_start'):
        subscription.current_period_start = datetime.fromtimestamp(
            stripe_data['current_period_start']
        )
    if stripe_data.get('current_period_end'):
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_data['current_period_end']
        )
