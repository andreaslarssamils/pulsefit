from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from orders.models import Order, OrderItem
from plans.models import Plan, PlanAccess, PlanCategory
from products.models import Product, ProductCategory

from .access import can_review
from .models import Review

User = get_user_model()

SIMPLE_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


def make_user(email="member@example.com", **kwargs):
    return User.objects.create_user(email=email, password="pw12345!", **kwargs)


def make_plan(title="12 Week Strength", **kwargs):
    cat, _ = PlanCategory.objects.get_or_create(name="Exercise", slug="exercise")
    return Plan.objects.create(
        category=cat, title=title, description="d", price=Decimal("49.00"), **kwargs
    )


def make_product(name="Resistance Bands", **kwargs):
    cat, _ = ProductCategory.objects.get_or_create(name="Merch", slug="merch")
    return Product.objects.create(
        category=cat, name=name, description="d", price=Decimal("19.00"),
        stock=10, **kwargs,
    )


def make_order(user, product, status="paid"):
    """Create an order."""
    order = Order.objects.create(
        user=user, order_number=Order.generate_order_number(),
        status=status, total=product.price,
    )
    OrderItem.objects.create(
        order=order, product=product, name=product.name,
        unit_price=product.price, quantity=1,
    )
    return order


def grant_plan(user, plan):
    """Give a user access to a plan."""
    PlanAccess.objects.create(user=user, plan=plan, source="purchase")


# --------------------------------------------------------------------------- #
# Cycle A — model constraints + can_review gate
# --------------------------------------------------------------------------- #
class ReviewConstraintTests(TestCase):
    """Test review model constraints."""
    def test_rejects_both_targets(self):
        # Key decision 1: exactly one of plan/product (mirrors OrderItem).
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    user=make_user(), plan=make_plan(), product=make_product(),
                    rating=5, body="x",
                )

    def test_rejects_no_target(self):
        """ Key decision 1: exactly one of plan/product (mirrors OrderItem)."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(user=make_user(), rating=5, body="x")

    def test_one_review_per_user_per_plan(self):
        """ One review per user per target."""
        user, plan = make_user(), make_plan()
        Review.objects.create(user=user, plan=plan, rating=5, body="great")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(user=user, plan=plan, rating=3, body="again")

    def test_one_review_per_user_per_product(self):
        """ One review per user per target."""
        user, product = make_user(), make_product()
        Review.objects.create(user=user, product=product, rating=5, body="great")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(user=user, product=product, rating=3, body="again")

    def test_two_users_can_review_same_plan(self):
        plan = make_plan()
        Review.objects.create(user=make_user("a@x.com"), plan=plan, rating=5, body="a")
        Review.objects.create(user=make_user("b@x.com"), plan=plan, rating=4, body="b")
        self.assertEqual(Review.objects.filter(plan=plan).count(), 2)

    def test_same_user_can_review_a_plan_and_a_product(self):
        # Conditional unique constraints must not collide across target types.
        user, plan, product = make_user(), make_plan(), make_product()
        Review.objects.create(user=user, plan=plan, rating=5, body="plan")
        Review.objects.create(user=user, product=product, rating=4, body="prod")
        self.assertEqual(Review.objects.filter(user=user).count(), 2)


class CanReviewTests(TestCase):
    def test_anonymous_cannot_review(self):
        self.assertFalse(can_review(AnonymousUser(), plan=make_plan()))
        self.assertFalse(can_review(AnonymousUser(), product=make_product()))

    def test_plan_access_allows_plan_review(self):
        # US-28: reviewer must hold PlanAccess for the plan.
        user, plan = make_user(), make_plan()
        grant_plan(user, plan)
        self.assertTrue(can_review(user, plan=plan))

    def test_without_plan_access_cannot_review_plan(self):
        self.assertFalse(can_review(make_user(), plan=make_plan()))

    def test_paid_order_allows_product_review(self):
        # US-28: reviewer must have a completed order containing the product.
        user, product = make_user(), make_product()
        make_order(user, product, status="paid")
        self.assertTrue(can_review(user, product=product))

    def test_shipped_order_allows_product_review(self):
        user, product = make_user(), make_product()
        make_order(user, product, status="shipped")
        self.assertTrue(can_review(user, product=product))

    def test_pending_order_does_not_allow_product_review(self):
        user, product = make_user(), make_product()
        make_order(user, product, status="pending")
        self.assertFalse(can_review(user, product=product))

    def test_no_order_cannot_review_product(self):
        self.assertFalse(can_review(make_user(), product=make_product()))


# --------------------------------------------------------------------------- #
# Cycle B — create/delete views + detail-page integration
# --------------------------------------------------------------------------- #
@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ReviewCreateViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.plan = make_plan()
        grant_plan(self.user, self.plan)
        self.add_url = reverse("reviews:add", args=["plan", self.plan.id])

    def test_login_required(self):
        resp = self.client.post(self.add_url, {"rating": 5, "body": "Nice"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/accounts/login/"))
        self.assertFalse(Review.objects.exists())

    def test_entitled_user_creates_review(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            self.add_url, {"rating": 5, "body": "Transformative plan"}, follow=True
        )
        self.assertRedirects(resp, self.plan.get_absolute_url())
        review = Review.objects.get()
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.plan, self.plan)
        self.assertEqual(review.rating, 5)
        self.assertContains(resp, "Review posted")

    def test_non_entitled_user_cannot_review(self):
        other = make_user("nope@example.com")
        self.client.force_login(other)
        resp = self.client.post(self.add_url, {"rating": 4, "body": "Sneaky"})
        self.assertFalse(Review.objects.exists())

    def test_resubmit_replaces_existing_review(self):
        # One review per user per target; edit replaces previous.
        self.client.force_login(self.user)
        self.client.post(self.add_url, {"rating": 2, "body": "First take"})
        resp = self.client.post(
            self.add_url, {"rating": 5, "body": "Changed my mind"}, follow=True
        )
        self.assertEqual(Review.objects.filter(user=self.user, plan=self.plan).count(), 1)
        review = Review.objects.get()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.body, "Changed my mind")
        self.assertContains(resp, "Review updated")

    def test_product_review_requires_paid_order(self):
        product = make_product()
        url = reverse("reviews:add", args=["product", product.id])
        buyer = make_user("buyer@example.com")
        make_order(buyer, product, status="paid")
        self.client.force_login(buyer)
        self.client.post(url, {"rating": 4, "body": "Sturdy bands"})
        self.assertTrue(Review.objects.filter(product=product, user=buyer).exists())

    def test_product_review_blocked_without_order(self):
        product = make_product()
        url = reverse("reviews:add", args=["product", product.id])
        self.client.force_login(make_user("browser@example.com"))
        self.client.post(url, {"rating": 4, "body": "Never bought"})
        self.assertFalse(Review.objects.filter(product=product).exists())


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ReviewDeleteViewTests(TestCase):
    def setUp(self):
        self.author = make_user("author@example.com")
        self.plan = make_plan()
        self.review = Review.objects.create(
            user=self.author, plan=self.plan, rating=5, body="My review"
        )
        self.delete_url = reverse("reviews:delete", args=[self.review.pk])

    def test_login_required(self):
        resp = self.client.post(self.delete_url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/accounts/login/"))
        self.assertTrue(Review.objects.filter(pk=self.review.pk).exists())

    def test_author_can_delete(self):
        self.client.force_login(self.author)
        resp = self.client.post(self.delete_url, follow=True)
        self.assertRedirects(resp, self.plan.get_absolute_url())
        self.assertFalse(Review.objects.filter(pk=self.review.pk).exists())
        self.assertContains(resp, "removed")

    def test_non_author_gets_404(self):
        self.client.force_login(make_user("intruder@example.com"))
        self.assertEqual(self.client.post(self.delete_url).status_code, 404)
        self.assertTrue(Review.objects.filter(pk=self.review.pk).exists())


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class DetailPageReviewIntegrationTests(TestCase):
    def test_plan_detail_shows_average_and_reviews(self):
        # US-28: average rating + reviews are displayed on the detail page.
        plan = make_plan()
        Review.objects.create(user=make_user("a@x.com"), plan=plan, rating=4, body="Solid programming")
        Review.objects.create(user=make_user("b@x.com"), plan=plan, rating=2, body="Too intense")
        resp = self.client.get(plan.get_absolute_url())
        self.assertContains(resp, "3.0")           # (4 + 2) / 2
        self.assertContains(resp, "(2)")
        self.assertContains(resp, "Solid programming")
        self.assertContains(resp, "Too intense")

    def test_plan_detail_shows_form_for_entitled_user(self):
        plan = make_plan()
        user = make_user()
        grant_plan(user, plan)
        self.client.force_login(user)
        resp = self.client.get(plan.get_absolute_url())
        self.assertContains(resp, 'name="body"')
        self.assertContains(resp, reverse("reviews:add", args=["plan", plan.id]))

    def test_plan_detail_hides_form_for_non_entitled_user(self):
        plan = make_plan()
        self.client.force_login(make_user())
        resp = self.client.get(plan.get_absolute_url())
        self.assertNotContains(resp, reverse("reviews:add", args=["plan", plan.id]))

    def test_product_detail_shows_average(self):
        product = make_product()
        Review.objects.create(user=make_user("c@x.com"), product=product, rating=5, body="Great bands")
        resp = self.client.get(product.get_absolute_url())
        self.assertContains(resp, "Great bands")
        self.assertContains(resp, "(1)")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ReviewAdminTests(TestCase):
    def setUp(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="pw12345!"
        )
        self.client.force_login(admin)

    def test_changelist_loads(self):
        resp = self.client.get(reverse("admin:reviews_review_changelist"))
        self.assertEqual(resp.status_code, 200)
