from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from blog.models import BlogPost
from plans.models import Plan, PlanCategory
from products.models import Product, ProductCategory

SIMPLE_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
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
        self.assertContains(resp, "<title>Marathon Base Builder — PulseFit</title>")
        self.assertContains(resp, 'property="og:title"')
        self.assertContains(resp, "Marathon Base Builder")
