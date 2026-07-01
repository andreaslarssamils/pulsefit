from decimal import Decimal

from plans.models import Plan
from products.models import Product

CART_SESSION_KEY = "cart"

ITEM_MODELS = {"plan": Plan, "product": Product}


class Cart:
    def __init__(self, request):
        self.session = request.session
        # Read-only: do not write the key here, or the nav-badge context
        # processor would persist an empty cart (and a session row) for every
        # anonymous visitor on every page. _save() writes back on mutation.
        self.cart = self.session.get(CART_SESSION_KEY, {})

    def add(self, item_type, item_id, qty=1):
        key = f"{item_type}:{item_id}"
        current_qty = self.cart.get(key, {}).get("qty", 0)
        self.cart[key] = {"qty": current_qty + qty}
        self._save()

    def update(self, item_type, item_id, qty):
        key = f"{item_type}:{item_id}"
        if key in self.cart:
            self.cart[key]["qty"] = qty
            self._save()

    def remove(self, item_type, item_id):
        key = f"{item_type}:{item_id}"
        if key in self.cart:
            del self.cart[key]
            self._save()

    def clear(self):
        self.cart = {}
        self._save()

    def items(self):
        """Resolve session entries to live Plan/Product objects with quantity
        and line total. Quantities for products are clamped to current stock
        (zero stock drops the item). Inactive or deleted items are dropped
        and pruned from the session silently."""
        resolved = []
        stale_keys = []
        for key, data in self.cart.items():
            item_type, item_id = key.split(":")
            item_id = int(item_id)
            qty = data["qty"]
            model = ITEM_MODELS.get(item_type)
            obj = model.objects.filter(pk=item_id, is_active=True).first() if model else None
            if obj is None:
                stale_keys.append(key)
                continue
            if item_type == "product":
                qty = min(qty, obj.stock)
            if qty <= 0:
                stale_keys.append(key)
                continue
            resolved.append({
                "key": key,
                "item_type": item_type,
                "object": obj,
                "qty": qty,
                "line_total": obj.price * qty,
            })
        for key in stale_keys:
            del self.cart[key]
        if stale_keys:
            self._save()
        return resolved

    def total(self):
        return sum((item["line_total"] for item in self.items()), Decimal("0"))

    def count(self):
        return sum(data["qty"] for data in self.cart.values())

    def _save(self):
        self.session[CART_SESSION_KEY] = self.cart
        self.session.modified = True
