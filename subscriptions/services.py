import logging
from datetime import datetime
from datetime import timezone as dt_timezone

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model

from plans.models import Plan, PlanAccess

from .models import Subscription

stripe.api_key = settings.STRIPE_SECRET_KEY
User = get_user_model()
logger = logging.getLogger(__name__)


def sync_subscription_access(subscription):
    """Idempotently reconcile PlanAccess(source='subscription') rows
    against the subscription's access state. Never touches
    source='purchase' rows."""
    user = subscription.user
    if subscription.is_active:
        for plan in Plan.objects.filter(premium_only=True, is_active=True):
            PlanAccess.objects.get_or_create(
                user=user, plan=plan, defaults={"source": "subscription"}
            )
    else:
        PlanAccess.objects.filter(user=user, source="subscription").delete()


def sync_from_stripe_subscription(stripe_sub):
    """Upsert the Subscription row from a Stripe subscription object, then
    reconcile access. Idempotent — safe on redelivered webhooks."""
    user = User.objects.filter(
        stripe_customer_id=stripe_sub["customer"]).first()
    if user is None:
        logger.warning(
            "No user for Stripe customer %s",
            stripe_sub["customer"])
        return
    period_end = stripe_sub["items"]["data"][0]["current_period_end"]
    sub, _ = Subscription.objects.update_or_create(
        user=user,
        defaults={
            "stripe_subscription_id": stripe_sub["id"],
            "stripe_customer_id": stripe_sub["customer"],
            "status": stripe_sub["status"],
            "current_period_end": datetime.fromtimestamp(
                period_end, tz=dt_timezone.utc
            ),
            "cancel_at_period_end": stripe_sub["cancel_at_period_end"],
        },
    )
    sync_subscription_access(sub)


def sync_from_checkout_session(session_id):
    """Fetch a completed Checkout Session's subscription and sync it locally.
    Safety net for the success redirect so activation doesn't depend solely on
    webhook timing/config. Idempotent with the webhook path (both funnel into
    sync_from_stripe_subscription, which is keyed by the Stripe customer)."""
    session = stripe.checkout.Session.retrieve(session_id)
    subscription_id = session.get("subscription")
    if not subscription_id:
        return
    stripe_sub = stripe.Subscription.retrieve(subscription_id)
    sync_from_stripe_subscription(stripe_sub)


def refresh_subscription_from_invoice(invoice):
    """Invoice events don't carry a stable subscription pointer across API
    versions; use our own row (keyed by the stable invoice customer) to fetch
    the authoritative subscription and re-sync."""
    user = User.objects.filter(stripe_customer_id=invoice["customer"]).first()
    if user is None:
        return
    sub = Subscription.objects.filter(user=user).first()
    if sub is None:
        return
    fresh = stripe.Subscription.retrieve(sub.stripe_subscription_id)
    sync_from_stripe_subscription(fresh)
