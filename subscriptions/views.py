import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Subscription
from .services import (
    refresh_subscription_from_invoice,
    sync_from_stripe_subscription,
)

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

_SUBSCRIPTION_EVENTS = {
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}
_INVOICE_EVENTS = {"invoice.payment_succeeded", "invoice.payment_failed"}


@csrf_exempt
@require_POST
def stripe_webhook(request):
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            request.body,
            sig_header,
            settings.STRIPE_SUBSCRIPTION_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        logger.warning("Subscription webhook signature verification failed")
        return HttpResponse(status=400)

    event_type = event["type"]
    obj = event["data"]["object"]
    if event_type in _SUBSCRIPTION_EVENTS:
        sync_from_stripe_subscription(obj)
    elif event_type in _INVOICE_EVENTS:
        refresh_subscription_from_invoice(obj)
    return HttpResponse(status=200)


def pricing(request):
    return render(request, "subscriptions/pricing.html")


@login_required
@require_POST
def subscribe(request):
    existing = Subscription.objects.filter(user=request.user).first()
    if existing and existing.is_active:
        return redirect("subscriptions:manage")

    if not request.user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=request.user.email, metadata={"user_id": request.user.id}
        )
        request.user.stripe_customer_id = customer.id
        request.user.save(update_fields=["stripe_customer_id"])

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=request.user.stripe_customer_id,
        line_items=[
            {
                "price": settings.STRIPE_PREMIUM_PRICE_ID,
                "quantity": 1}],
        client_reference_id=str(
            request.user.id),
        success_url=request.build_absolute_uri(
            reverse("subscriptions:manage")) +
        "?checkout=success",
        cancel_url=request.build_absolute_uri(
            reverse("subscriptions:pricing")),
    )
    return redirect(session.url)


@login_required
def manage(request):
    subscription = Subscription.objects.filter(user=request.user).first()
    if request.GET.get("checkout") == "success":
        messages.success(
            request,
            "Welcome to PulseFit Premium! Your subscription is being "
            "activated.",
        )
    return render(
        request,
        "subscriptions/manage.html",
        {"subscription": subscription}
    )


@login_required
@require_POST
def cancel(request):
    subscription = Subscription.objects.filter(user=request.user).first()
    if (
        subscription
        and subscription.is_active
        and not subscription.cancel_at_period_end
    ):
        stripe.Subscription.modify(
            subscription.stripe_subscription_id, cancel_at_period_end=True
        )
        subscription.cancel_at_period_end = True
        subscription.save(update_fields=["cancel_at_period_end"])
        messages.success(request, "Your subscription will not renew.")
    return redirect("subscriptions:manage")
