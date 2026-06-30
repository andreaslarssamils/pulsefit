"""
Seed the catalog with sample data.

    .venv/bin/python manage.py seed_catalog
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from products.models import Product, ProductCategory

from plans.models import Plan, PlanCategory

PLAN_CATEGORIES = [("Exercise", "exercise"), ("Nutrition", "nutrition")]
PRODUCT_CATEGORIES = [
    ("Exercise", "exercise"),
    ("Nutrition", "nutrition"),
    ("Merch", "merch"),
]

PLANS = [
    {
        "slug": "12-week-strength",
        "title": "12 Week Strength",
        "category": "exercise",
        "description": "A progressive 12-week barbell program to build raw, full-body strength.",
        "price": Decimal("49.00"),
        "premium_only": False,
    },
    {
        "slug": "elite-hypertrophy",
        "title": "Elite Hypertrophy",
        "category": "exercise",
        "description": "Advanced high-volume training for serious muscle growth. Premium members only.",
        "price": Decimal("99.00"),
        "premium_only": True,
    },
    {
        "slug": "lean-nutrition-blueprint",
        "title": "Lean Nutrition Blueprint",
        "category": "nutrition",
        "description": "A flexible meal-planning system to lose fat without giving up the foods you love.",
        "price": Decimal("39.00"),
        "premium_only": False,
    },
]

PRODUCTS = [
    {
        "slug": "resistance-bands-set",
        "name": "Resistance Bands Set",
        "category": "exercise",
        "description": "Five premium latex resistance bands with carry bag — train anywhere.",
        "price": Decimal("29.00"),
        "stock": 25,
    },
    {
        "slug": "whey-protein-1kg",
        "name": "Whey Protein 1kg",
        "category": "nutrition",
        "description": "Grass-fed whey isolate, 25g protein per serving. Currently sold out.",
        "price": Decimal("34.00"),
        "stock": 0,
    },
    {
        "slug": "pulsefit-training-tee",
        "name": "PulseFit Training Tee",
        "category": "merch",
        "description": "Breathable performance tee with the PulseFit logo.",
        "price": Decimal("25.00"),
        "stock": 12,
    },
]


class Command(BaseCommand):
    help = "Seed the catalog with sample plans and products (dev only, idempotent)."

    def handle(self, *args, **options):
        plan_cats = {
            slug: PlanCategory.objects.get_or_create(
                slug=slug, defaults={"name": name}
            )[0]
            for name, slug in PLAN_CATEGORIES
        }
        product_cats = {
            slug: ProductCategory.objects.get_or_create(
                slug=slug, defaults={"name": name}
            )[0]
            for name, slug in PRODUCT_CATEGORIES
        }

        plans_created = 0
        for data in PLANS:
            fields = {k: v for k, v in data.items() if k not in ("slug", "category")}
            fields["category"] = plan_cats[data["category"]]
            _, created = Plan.objects.get_or_create(slug=data["slug"], defaults=fields)
            plans_created += int(created)

        products_created = 0
        for data in PRODUCTS:
            fields = {k: v for k, v in data.items() if k not in ("slug", "category")}
            fields["category"] = product_cats[data["category"]]
            _, created = Product.objects.get_or_create(
                slug=data["slug"], defaults=fields
            )
            products_created += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog seeded: +{plans_created} plans, +{products_created} products "
                f"(categories ensured). Re-running is safe."
            )
        )
