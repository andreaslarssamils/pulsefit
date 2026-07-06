from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from plans.access import has_plan_access
from plans.models import Plan, PlanAccess, PlanCategory

User = get_user_model()

# Plain static storage so rendering pages that call {% static %}
# does not depend
# on `collectstatic` having built the manifest first (mirrors
# accounts/tests.py).
SIMPLE_STATIC_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def make_category(name="Exercise", slug="exercise"):
    return PlanCategory.objects.create(name=name, slug=slug)


def make_plan(category=None, **kwargs):
    category = category or make_category()
    defaults = {
        "category": category,
        "title": "12 Week Strength",
        "description": "Build raw strength over 12 weeks.",
        "price": Decimal("49.00"),
    }
    defaults.update(kwargs)
    return Plan.objects.create(**defaults)


class PlanModelTests(TestCase):
    def test_category_str_is_name(self):
        self.assertEqual(
            str(make_category(name="Nutrition", slug="nutrition")), "Nutrition"
        )

    def test_slug_is_autofilled_from_title_when_blank(self):
        plan = make_plan(title="12 Week Strength")
        self.assertEqual(plan.slug, "12-week-strength")

    def test_explicit_slug_is_preserved(self):
        plan = make_plan(slug="custom-slug")
        self.assertEqual(plan.slug, "custom-slug")

    def test_str_is_title(self):
        self.assertEqual(
            str(make_plan(title="Mobility Reset")), "Mobility Reset")

    def test_get_absolute_url_uses_slug(self):
        plan = make_plan(title="Mobility Reset")
        self.assertEqual(plan.get_absolute_url(), f"/plans/{plan.slug}/")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class PlanListViewTests(TestCase):
    def test_list_returns_200(self):
        resp = self.client.get(reverse("plans:list"))
        self.assertEqual(resp.status_code, 200)

    def test_list_shows_active_plan(self):
        make_plan(title="Active Plan", slug="active-plan")
        resp = self.client.get(reverse("plans:list"))
        self.assertContains(resp, "Active Plan")

    def test_list_excludes_inactive_plan(self):
        make_plan(title="Hidden Plan", slug="hidden-plan", is_active=False)
        resp = self.client.get(reverse("plans:list"))
        self.assertNotContains(resp, "Hidden Plan")

    def test_list_renders_category_as_filter_tab(self):
        make_plan(category=make_category(name="Nutrition", slug="nutrition"))
        resp = self.client.get(reverse("plans:list"))
        self.assertContains(resp, 'data-filter="nutrition"')

    def test_card_carries_data_category_for_clientside_filter(self):
        cat = make_category(name="Nutrition", slug="nutrition")
        make_plan(category=cat, title="Macro Mastery", slug="macro-mastery")
        resp = self.client.get(reverse("plans:list"))
        self.assertContains(resp, 'data-category="nutrition"')

    def test_premium_badge_rendered_on_premium_card(self):
        make_plan(title="Elite Program", slug="elite", premium_only=True)
        resp = self.client.get(reverse("plans:list"))
        self.assertContains(resp, "badge--premium")

    def test_empty_state_visible_when_catalog_empty(self):
        resp = self.client.get(reverse("plans:list"))
        self.assertContains(resp, "No plans yet")
        self.assertNotContains(resp, "data-empty-state hidden")

    def test_empty_state_hidden_when_plans_exist(self):
        make_plan()
        resp = self.client.get(reverse("plans:list"))
        self.assertContains(resp, "data-empty-state hidden")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class PlanDetailViewTests(TestCase):
    def test_detail_returns_200_for_active_plan(self):
        plan = make_plan(title="Active Plan", slug="active-plan")
        resp = self.client.get(plan.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Active Plan")

    def test_detail_404_for_inactive_plan(self):
        plan = make_plan(slug="hidden-plan", is_active=False)
        resp = self.client.get(
            reverse(
                "plans:detail",
                kwargs={
                    "slug": plan.slug}))
        self.assertEqual(resp.status_code, 404)

    def test_detail_404_for_unknown_slug(self):
        resp = self.client.get(
            reverse(
                "plans:detail",
                kwargs={
                    "slug": "nope"}))
        self.assertEqual(resp.status_code, 404)

    def test_premium_plan_shows_go_premium_cta(self):
        plan = make_plan(slug="elite", premium_only=True)
        resp = self.client.get(plan.get_absolute_url())
        self.assertContains(resp, "Go Premium")

    def test_free_plan_shows_add_to_cart(self):
        plan = make_plan(slug="free-plan", premium_only=False)
        resp = self.client.get(plan.get_absolute_url())
        self.assertContains(resp, "Add to Cart")

    def test_add_to_cart_form_posts_to_cart_add_url(self):
        plan = make_plan(slug="free-plan", premium_only=False)
        resp = self.client.get(plan.get_absolute_url())
        self.assertContains(resp, f'action="/cart/add/plan/{plan.id}/"')


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class PlanAdminTests(TestCase):
    """Catalog models are manageable from Django admin."""

    def setUp(self):
        admin = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pw12345!"
        )
        self.client.force_login(admin)

    def test_plancategory_changelist_loads(self):
        resp = self.client.get(reverse("admin:plans_plancategory_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_plan_changelist_loads(self):
        resp = self.client.get(reverse("admin:plans_plan_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_plan_add_form_loads(self):
        resp = self.client.get(reverse("admin:plans_plan_add"))
        self.assertEqual(resp.status_code, 200)


class PlanAccessModelTests(TestCase):
    """PlanAccess rows gate access to premium content."""
    def setUp(self):
        self.cat = PlanCategory.objects.create(
            name="Exercise", slug="exercise")
        self.plan = Plan.objects.create(
            category=self.cat,
            title="12 Week Strength",
            description="x",
            price="49.00")
        self.user = User.objects.create_user(
            email="a@example.com", password="pw12345!")

    def test_has_access_false_without_row(self):
        self.assertFalse(has_plan_access(self.user, self.plan))

    def test_has_access_true_with_purchase_row(self):
        PlanAccess.objects.create(
            user=self.user,
            plan=self.plan,
            source="purchase")
        self.assertTrue(has_plan_access(self.user, self.plan))

    def test_has_access_true_with_subscription_row(self):
        PlanAccess.objects.create(
            user=self.user,
            plan=self.plan,
            source="subscription")
        self.assertTrue(has_plan_access(self.user, self.plan))

    def test_has_access_false_for_anonymous(self):
        PlanAccess.objects.create(
            user=self.user,
            plan=self.plan,
            source="purchase")
        self.assertFalse(has_plan_access(AnonymousUser(), self.plan))

    def test_one_access_row_per_user_plan(self):
        PlanAccess.objects.create(
            user=self.user,
            plan=self.plan,
            source="purchase")
        with self.assertRaises(IntegrityError), transaction.atomic():
            PlanAccess.objects.create(
                user=self.user, plan=self.plan, source="subscription"
            )


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class PlanDetailGatingTests(TestCase):
    """ Premium plans show "Go Premium"
    CTA to users without access, and
    """
    def setUp(self):
        self.cat = PlanCategory.objects.create(
            name="Exercise", slug="exercise")
        self.premium = Plan.objects.create(
            category=self.cat,
            title="Elite",
            slug="elite",
            description="x",
            price="99.00",
            premium_only=True,
        )
        self.paid = Plan.objects.create(
            category=self.cat,
            title="Strength",
            slug="strength",
            description="x",
            price="49.00",
            premium_only=False,
        )
        self.user = User.objects.create_user(
            email="a@example.com", password="pw12345!")

    def test_premium_without_access_shows_go_premium(self):
        resp = self.client.get(
            reverse(
                "plans:detail",
                kwargs={
                    "slug": "elite"}))
        self.assertContains(resp, "Go Premium")

    def test_nonpremium_without_access_shows_add_to_cart(self):
        resp = self.client.get(
            reverse(
                "plans:detail",
                kwargs={
                    "slug": "strength"}))
        self.assertContains(resp, "Add to Cart")

    def test_with_access_shows_access_content(self):
        PlanAccess.objects.create(
            user=self.user, plan=self.premium, source="subscription"
        )
        self.client.force_login(self.user)
        resp = self.client.get(
            reverse(
                "plans:detail",
                kwargs={
                    "slug": "elite"}))
        self.assertContains(resp, "Access Content")
