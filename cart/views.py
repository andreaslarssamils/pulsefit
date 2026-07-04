from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import ITEM_MODELS, Cart


def _redirect_back(request, default="cart:detail"):
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return redirect(referer)
    return redirect(default)


@require_POST
def add_to_cart(request, item_type, item_id):
    model = ITEM_MODELS.get(item_type)
    if model is None:
        return redirect("cart:detail")

    lookup = {"pk": item_id, "is_active": True}
    if item_type == "plan":
        lookup["premium_only"] = False
    obj = get_object_or_404(model, **lookup)

    Cart(request).add(item_type, item_id)
    name = obj.title if item_type == "plan" else obj.name
    messages.success(request, f"Added {name} to your cart.")
    return _redirect_back(request)


def cart_detail(request):
    cart = Cart(request)
    return render(request, "cart/cart_detail.html", {
        "cart_items": cart.items(),
        "cart_total": cart.total(),
    })


@require_POST
def update_cart(request, item_type, item_id):
    try:
        qty = int(request.POST.get("qty", 1))
    except (TypeError, ValueError):
        qty = 1
    qty = max(qty, 1)
    Cart(request).update(item_type, item_id, qty)
    messages.success(request, "Cart updated.")
    return redirect("cart:detail")


@require_POST
def remove_from_cart(request, item_type, item_id):
    Cart(request).remove(item_type, item_id)
    messages.success(request, "Item removed from cart.")
    return redirect("cart:detail")
