from decimal import Decimal

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from cart.cart import Cart
from plans.models import Plan, PlanCategory
from products.models import Product, ProductCategory


def make_request():
    request = RequestFactory().get("/")
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    return request


def make_plan(**kwargs):
    category = PlanCategory.objects.create(name="Exercise", slug="exercise")
    defaults = {
        "category": category,
        "title": "12 Week Strength",
        "description": "Build raw strength over 12 weeks.",
        "price": Decimal("49.00"),
    }
    defaults.update(kwargs)
    return Plan.objects.create(**defaults)


def make_product(**kwargs):
    category = ProductCategory.objects.create(name="Merch", slug="merch")
    defaults = {
        "category": category,
        "name": "Resistance Bands",
        "description": "A set of premium resistance bands.",
        "price": Decimal("29.00"),
        "stock": 10,
    }
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


class CartTests(TestCase):
    def test_add_new_item_sets_quantity(self):
        cart = Cart(make_request())
        plan = make_plan()
        cart.add("plan", plan.id, qty=1)
        self.assertEqual(cart.count(), 1)

    def test_add_same_item_twice_increments_quantity(self):
        cart = Cart(make_request())
        plan = make_plan()
        cart.add("plan", plan.id, qty=1)
        cart.add("plan", plan.id, qty=1)
        self.assertEqual(cart.count(), 2)

    def test_update_sets_exact_quantity(self):
        cart = Cart(make_request())
        product = make_product()
        cart.add("product", product.id, qty=1)
        cart.update("product", product.id, qty=5)
        self.assertEqual(cart.count(), 5)

    def test_remove_drops_item(self):
        cart = Cart(make_request())
        product = make_product()
        cart.add("product", product.id, qty=1)
        cart.remove("product", product.id)
        self.assertEqual(cart.count(), 0)

    def test_items_resolves_live_objects_with_line_total(self):
        cart = Cart(make_request())
        product = make_product(price=Decimal("29.00"))
        cart.add("product", product.id, qty=2)
        items = cart.items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["object"], product)
        self.assertEqual(items[0]["qty"], 2)
        self.assertEqual(items[0]["line_total"], Decimal("58.00"))

    def test_items_drops_inactive_plan_and_prunes_session(self):
        cart = Cart(make_request())
        plan = make_plan(is_active=True)
        cart.add("plan", plan.id, qty=1)
        plan.is_active = False
        plan.save()
        self.assertEqual(cart.items(), [])
        self.assertEqual(cart.count(), 0)

    def test_items_clamps_product_quantity_to_stock(self):
        cart = Cart(make_request())
        product = make_product(stock=2)
        cart.add("product", product.id, qty=5)
        items = cart.items()
        self.assertEqual(items[0]["qty"], 2)

    def test_items_drops_product_with_zero_stock(self):
        cart = Cart(make_request())
        product = make_product(stock=0)
        cart.add("product", product.id, qty=1)
        self.assertEqual(cart.items(), [])

    def test_total_sums_line_totals_across_items(self):
        cart = Cart(make_request())
        plan = make_plan(price=Decimal("49.00"))
        product = make_product(price=Decimal("29.00"), stock=10)
        cart.add("plan", plan.id, qty=1)
        cart.add("product", product.id, qty=2)
        self.assertEqual(cart.total(), Decimal("107.00"))

    def test_clear_empties_cart(self):
        cart = Cart(make_request())
        cart.add("plan", make_plan().id, qty=1)
        cart.clear()
        self.assertEqual(cart.count(), 0)

    def test_reading_cart_does_not_persist_empty_cart_for_new_visitor(self):
        # The nav badge builds a Cart on every request; merely reading it must
        # not write an empty cart into the session (which would force a
        # DB-backed session + cookie for every anonymous visitor,
        # defeating lazy sessions).
        request = make_request()
        cart = Cart(request)
        self.assertEqual(cart.count(), 0)
        self.assertNotIn("cart", request.session)


SIMPLE_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class AddToCartViewTests(TestCase):
    def test_add_to_cart_redirects_and_increments_session(self):
        plan = make_plan()
        resp = self.client.post(reverse("cart:add", args=["plan", plan.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            self.client.session["cart"], {
                f"plan:{
                    plan.id}": {
                    "qty": 1}})

    def test_add_to_cart_shows_success_message(self):
        plan = make_plan(title="12 Week Strength")
        resp = self.client.post(
            reverse(
                "cart:add",
                args=[
                    "plan",
                    plan.id]),
            follow=True)
        messages = list(resp.context["messages"])
        self.assertIn("12 Week Strength", str(messages[0]))

    def test_add_to_cart_rejects_premium_only_plan(self):
        plan = make_plan(premium_only=True)
        resp = self.client.post(reverse("cart:add", args=["plan", plan.id]))
        self.assertEqual(resp.status_code, 404)

    def test_add_to_cart_rejects_unknown_item_type(self):
        resp = self.client.post(reverse("cart:add", args=["widget", 1]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_add_to_cart_get_not_allowed(self):
        plan = make_plan()
        resp = self.client.get(reverse("cart:add", args=["plan", plan.id]))
        self.assertEqual(resp.status_code, 405)


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class CartDetailViewTests(TestCase):
    def test_cart_detail_returns_200(self):
        resp = self.client.get(reverse("cart:detail"))
        self.assertEqual(resp.status_code, 200)

    def test_cart_detail_shows_items_and_total(self):
        product = make_product(name="Resistance Bands", price=Decimal("29.00"))
        self.client.post(reverse("cart:add", args=["product", product.id]))
        resp = self.client.get(reverse("cart:detail"))
        self.assertContains(resp, "Resistance Bands")
        self.assertContains(resp, "29.00")

    def test_cart_detail_shows_empty_state_when_no_items(self):
        resp = self.client.get(reverse("cart:detail"))
        self.assertContains(resp, "Your cart is empty")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class UpdateRemoveCartViewTests(TestCase):
    def test_update_cart_changes_quantity(self):
        product = make_product()
        self.client.post(reverse("cart:add", args=["product", product.id]))
        self.client.post(
            reverse(
                "cart:update", args=[
                    "product", product.id]), {
                "qty": 3})
        self.assertEqual(
            self.client.session["cart"][f"product:{product.id}"]["qty"], 3)

    def test_update_cart_ignores_non_numeric_qty(self):
        product = make_product()
        self.client.post(reverse("cart:add", args=["product", product.id]))
        self.client.post(
            reverse(
                "cart:update", args=[
                    "product", product.id]), {
                "qty": "abc"})
        self.assertEqual(
            self.client.session["cart"][f"product:{product.id}"]["qty"], 1)

    def test_remove_from_cart_drops_item(self):
        product = make_product()
        self.client.post(reverse("cart:add", args=["product", product.id]))
        self.client.post(reverse("cart:remove", args=["product", product.id]))
        self.assertEqual(self.client.session["cart"], {})


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class CartBadgeTests(TestCase):
    def test_nav_shows_no_badge_when_cart_empty(self):
        resp = self.client.get(reverse("plans:list"))
        self.assertNotContains(resp, "cart-badge")

    def test_nav_shows_badge_with_count_when_cart_has_items(self):
        plan = make_plan()
        self.client.post(reverse("cart:add", args=["plan", plan.id]))
        resp = self.client.get(reverse("plans:list"))
        self.assertContains(resp, "cart-badge")
        self.assertContains(resp, ">1<")
