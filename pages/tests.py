from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from blog.models import BlogPost
from orders.models import Order
from plans.models import Plan, PlanCategory
from products.models import Product, ProductCategory

User = get_user_model()

SIMPLE_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class SitemapTests(TestCase):
    """U /sitemap.xml lists public pages, plans, products and blog posts."""

    def setUp(self):
        cat = PlanCategory.objects.create(name="Exercise", slug="exercise")
        self.plan = Plan.objects.create(
            category=cat,
            title="12 Week Strength",
            description="d",
            price=Decimal("49")
        )
        pcat = ProductCategory.objects.create(name="Merch", slug="merch")
        self.product = Product.objects.create(
            category=pcat,
            name="Resistance Bands",
            description="d",
            price=Decimal("19"),
            stock=5,
        )
        self.post = BlogPost.objects.create(
            title="Fitness 101", body="b", status="published"
        )

    def test_sitemap_is_served(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("xml", resp["Content-Type"])

    def test_sitemap_lists_catalog_and_blog(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, self.plan.get_absolute_url())
        self.assertContains(resp, self.product.get_absolute_url())
        self.assertContains(resp, self.post.get_absolute_url())

    def test_sitemap_lists_static_pages(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, reverse("plans:list"))
        self.assertContains(resp, reverse("subscriptions:pricing"))
        self.assertContains(resp, reverse("blog:list"))

    def test_sitemap_excludes_draft_posts(self):
        BlogPost.objects.create(title="Hidden Draft", body="b", status="draft")
        resp = self.client.get("/sitemap.xml")
        draft = BlogPost.objects.get(title="Hidden Draft")
        self.assertNotContains(resp, draft.get_absolute_url())


class RobotsTxtTests(TestCase):
    """/robots.txt disallows private areas and names the sitemap."""

    def test_robots_is_served_as_plain_text(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp["Content-Type"])

    def test_robots_disallows_private_paths(self):
        content = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /admin/", content)
        self.assertIn("Disallow: /dashboard/", content)
        self.assertIn("Disallow: /orders/", content)
        self.assertIn("Disallow: /cart/", content)

    def test_robots_names_the_sitemap(self):
        content = self.client.get("/robots.txt").content.decode()
        self.assertIn("Sitemap:", content)
        self.assertIn("/sitemap.xml", content)


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class MetaTagTests(TestCase):
    """ descriptive title + meta description + Open Graph tags."""

    def test_home_has_open_graph_tags(self):
        resp = self.client.get("/")
        self.assertContains(resp, 'property="og:site_name"')
        self.assertContains(resp, 'property="og:type"')
        self.assertContains(resp, 'property="og:url"')

    def test_home_has_meta_description(self):
        self.assertContains(self.client.get("/"), 'name="description"')

    def test_plan_detail_title_and_og_reflect_the_plan(self):
        cat = PlanCategory.objects.create(name="Exercise", slug="exercise")
        plan = Plan.objects.create(
            category=cat,
            title="Marathon Base Builder",
            description="Long runs",
            price=Decimal("59"),
        )
        resp = self.client.get(plan.get_absolute_url())
        self.assertContains(
            resp,
            "<title>Marathon Base Builder — PulseFit</title>"
        )
        self.assertContains(resp, 'property="og:title"')
        self.assertContains(resp, "Marathon Base Builder")


def make_user(email="member@example.com", **kwargs):
    return User.objects.create_user(email=email, password="pw12345!", **kwargs)


def make_plan():
    cat = PlanCategory.objects.create(name="Exercise", slug="exercise")
    return Plan.objects.create(
        category=cat,
        title="12 Week Strength",
        description="d",
        price=Decimal("49")
    )


def make_product():
    cat = ProductCategory.objects.create(name="Merch", slug="merch")
    return Product.objects.create(
        category=cat,
        name="Resistance Bands",
        description="d",
        price=Decimal("19"),
        stock=10,
    )


def message_texts(response):
    return [str(m) for m in response.context["messages"]]


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class FlashMessageAuditTests(TestCase):
    """US-38: success/error messages on key actions + dismissible toasts."""

    def test_toasts_are_dismissible(self):
        plan = make_plan()
        resp = self.client.post(
            reverse("cart:add", args=["plan", plan.id]), follow=True
        )
        self.assertContains(resp, "toast__close")

    def test_cart_update_shows_message(self):
        product = make_product()
        self.client.post(reverse("cart:add", args=["product", product.id]))
        resp = self.client.post(
            reverse("cart:update", args=["product", product.id]),
            {"qty": 3},
            follow=True,
        )
        self.assertTrue(message_texts(resp))

    def test_cart_remove_shows_message(self):
        product = make_product()
        self.client.post(reverse("cart:add", args=["product", product.id]))
        resp = self.client.post(
            reverse("cart:remove", args=["product", product.id]), follow=True
        )
        self.assertTrue(message_texts(resp))

    def test_order_success_shows_confirmation_message(self):
        user = make_user()
        self.client.force_login(user)
        order = Order.objects.create(
            user=user,
            order_number="PF-TEST0001",
            status="paid",
            total=Decimal("49"),
            stripe_checkout_session_id="sess_abc",
        )
        resp = self.client.get(reverse(
            "orders:success") +
            "?session_id=sess_abc"
        )
        self.assertIn(order.order_number, " ".join(message_texts(resp)))

    def test_order_cancel_shows_message(self):
        resp = self.client.get(reverse("orders:cancel"))
        self.assertTrue(message_texts(resp))

    def test_subscription_return_shows_welcome_message(self):
        self.client.force_login(make_user())
        resp = self.client.get(reverse(
            "subscriptions:manage") +
            "?checkout=success"
        )
        self.assertIn("Premium", " ".join(message_texts(resp)))

    def test_invalid_goal_form_shows_error_message(self):
        self.client.force_login(make_user())
        resp = self.client.post(reverse("dashboard:set_goal"), {})
        self.assertIn("fix the errors", " ".join(message_texts(resp)).lower())

    def test_invalid_community_post_shows_error_message(self):
        self.client.force_login(make_user())
        resp = self.client.post(reverse(
            "community:post_create"),
            {"body": "   "}
        )
        self.assertIn("fix the errors", " ".join(message_texts(resp)).lower())

    def test_login_emits_message(self):
        make_user(email="login@example.com")
        resp = self.client.post(
            reverse("account_login"),
            {"login": "login@example.com", "password": "pw12345!"},
            follow=True,
        )
        self.assertTrue(message_texts(resp))
