"""
Stripe client helper module.

Provides centralized Stripe configuration and client access.
"""
import stripe
from django.conf import settings


def get_stripe_client():
    """
    Returns a configured Stripe client.
    Raises an error if Stripe is not configured.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise ValueError(
            "Stripe is not configured. Set STRIPE_SECRET_KEY in environment variables."
        )
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def is_stripe_configured():
    """Check if Stripe keys are configured."""
    return bool(settings.STRIPE_SECRET_KEY)
