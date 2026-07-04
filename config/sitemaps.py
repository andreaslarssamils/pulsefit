from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from blog.models import BlogPost
from plans.models import Plan
from products.models import Product


class StaticViewSitemap(Sitemap):
    """Public landing pages: home, plans, shop, pricing, blog."""

    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return [
            "core:home",
            "plans:list",
            "products:list",
            "subscriptions:pricing",
            "blog:list",
        ]

    def location(self, item):
        return reverse(item)


class PlanSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Plan.objects.filter(is_active=True)


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Product.objects.filter(is_active=True)


class BlogPostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return BlogPost.objects.filter(status="published")

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "static": StaticViewSitemap,
    "plans": PlanSitemap,
    "products": ProductSitemap,
    "blog": BlogPostSitemap,
}
