import json
import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cart.cart import Cart
from plans.models import PlanAccess
from products.models import Product

from .emails import send_order_confirmation_email
from .models import Order, OrderItem

stripe.api_key = settings.STRIPE_SECRET_KEY

User = get_user_model()
logger = logging.getLogger(__name__)


@login_required
def checkout_view(request):
    """Handle the checkout process."""
    if request.method != "POST":
        messages.info(
            request,
            "You're signed in — review your cart and continue to checkout.")
        return redirect("cart:detail")
    cart = Cart(request)
    items = cart.items()
    if not items:
        return redirect("cart:detail")

    line_items = []
    cart_snapshot = []
    needs_shipping = False
    for entry in items:
        obj = entry["object"]
        name = obj.title if entry["item_type"] == "plan" else obj.name
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": name},
                    "unit_amount": int(obj.price * 100),
                },
                "quantity": entry["qty"],
            }
        )
        cart_snapshot.append(
            {
                "t": entry["item_type"],
                "id": obj.id,
                "q": entry["qty"],
                "name": name,
                "price": str(obj.price),
            }
        )
        if entry["item_type"] == "product" and not obj.is_digital:
            needs_shipping = True

    session_kwargs = {
        "mode": "payment",
        "line_items": line_items,
        "success_url": request.build_absolute_uri(reverse("orders:success"))
        + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": request.build_absolute_uri(reverse("orders:cancel")),
        "client_reference_id": str(request.user.id),
        "metadata": {"cart": json.dumps(cart_snapshot)},
    }
    if needs_shipping:
        # Adjust this list to the countries PulseFit actually ships to.
        session_kwargs["shipping_address_collection"] = {
            "allowed_countries": ["US", "CA", "GB", "SE"]
        }

    session = stripe.checkout.Session.create(**session_kwargs)
    return redirect(session.url)


def order_success_view(request):
    """ Handle the order success page after a successful checkout."""
    session_id = request.GET.get("session_id", "")
    order = Order.objects.filter(stripe_checkout_session_id=session_id).first()
    if order:
        messages.success(
            request,
            f"Payment received — order {order.order_number} is confirmed."
        )
        if request.user.is_authenticated and order.user_id == request.user.id:
            Cart(request).clear()
    return render(request, "orders/order_success.html", {"order": order})


def order_cancel_view(request):
    messages.info(request, "Checkout canceled — your cart is still saved.")
    return render(request, "orders/order_cancel.html")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """ Handle Stripe webhook events for order processing."""
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        logger.warning("Stripe webhook signature verification failed")
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Live webhooks deliver a StripeObject, which since stripe 15 is not a
        # dict subclass and has no .get(); normalise to a plain (recursively
        # converted) dict so the handler can use .get()/[] uniformly.
        if not isinstance(session, dict):
            session = json.loads(str(session))
        if session.get("mode") == "payment":
            _handle_checkout_completed(session)
        # subscription-mode completions are handled by the subscriptions
        # webhook

    return HttpResponse(status=200)


def _handle_checkout_completed(session):
    if Order.objects.filter(stripe_checkout_session_id=session["id"]).exists():
        logger.info(
            "Duplicate webhook delivery for session %s, skipping",
            session["id"])
        return  # Stripe may deliver the same event more than once.

    user = get_object_or_404(User, pk=session["client_reference_id"])
    cart_snapshot = json.loads(session["metadata"]["cart"])
    # `shipping_details` on newer API versions, `shipping` on
    # 2020-08-27 — read both so a physical order captures the address
    # regardless of event shape.
    shipping = session.get("shipping_details") or session.get("shipping") or {}
    address = shipping.get("address") or {}

    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                order_number=Order.generate_order_number(),
                status="paid",
                total=(
                    Decimal(
                        session["amount_total"]) /
                    100).quantize(
                    Decimal("0.01")),
                stripe_checkout_session_id=session["id"],
                shipping_name=shipping.get("name") or "",
                shipping_address_line1=address.get("line1") or "",
                shipping_address_line2=address.get("line2") or "",
                shipping_city=address.get("city") or "",
                shipping_postal_code=address.get("postal_code") or "",
                shipping_country=address.get("country") or "",
            )

            for entry in cart_snapshot:
                item_kwargs = {
                    "order": order,
                    "name": entry["name"],
                    "unit_price": Decimal(entry["price"]),
                    "quantity": entry["q"],
                }
                if entry["t"] == "plan":
                    item_kwargs["plan_id"] = entry["id"]
                    PlanAccess.objects.get_or_create(
                        user=user,
                        plan_id=entry["id"],
                        defaults={"source": "purchase", "order": order},
                    )
                else:
                    item_kwargs["product_id"] = entry["id"]
                    Product.objects.filter(pk=entry["id"]).update(
                        stock=Greatest(F("stock") - entry["q"], 0)
                    )
                OrderItem.objects.create(**item_kwargs)
    except IntegrityError:
        # A concurrent duplicate delivery already created this order (the
        # exists() check above isn't atomic). Treat as already handled.
        logger.info(
            "Concurrent duplicate for session %s, skipping", session["id"]
        )
        return

    send_order_confirmation_email(order)
