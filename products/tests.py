
# Create your tests here.
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse

from products.models import Product, ProductCategory

User = get_user_model()

# Plain static storage so rendering pages that call {% static %} does not
# depend on `collectstatic` having built the manifest first (mirrors
# plans/tests.py).
SIMPLE_STATIC_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def make_category(name="Exercise", slug="exercise"):
    return ProductCategory.objects.create(name=name, slug=slug)


def make_product(category=None, **kwargs):
    category = category or make_category()
    defaults = {
        "category": category,
        "name": "Resistance Bands",
        "description": "A set of durable resistance bands.",
        "price": Decimal("29.99"),
        "stock": 10,
    }
    defaults.update(kwargs)
    return Product.objects.create(**defaults)


class ProductModelTests(TestCase):
    def test_category_str_is_name(self):
        category = make_category(name="Nutrition", slug="nutrition")
        self.assertEqual(str(category), "Nutrition")

    def test_category_verbose_name_plural(self):
        self.assertEqual(
            ProductCategory._meta.verbose_name_plural,
            "product categories",
        )

    def test_product_str_is_name(self):
        self.assertEqual(str(make_product(name="Foam Roller")), "Foam Roller")

    def test_slug_autofilled_from_name_when_blank(self):
        product = make_product(name="Resistance Bands")
        self.assertEqual(product.slug, "resistance-bands")

    def test_explicit_slug_is_preserved(self):
        product = make_product(slug="custom-slug")
        self.assertEqual(product.slug, "custom-slug")

    def test_get_absolute_url_uses_slug(self):
        product = make_product(name="Foam Roller")
        self.assertEqual(product.get_absolute_url(), f"/shop/{product.slug}/")

    def test_in_stock_true_when_stock_positive(self):
        self.assertTrue(make_product(stock=3).in_stock)

    def test_in_stock_false_when_stock_zero(self):
        self.assertFalse(make_product(stock=0).in_stock)

    def test_products_ordered_by_name(self):
        cat = make_category()
        make_product(category=cat, name="Banana", slug="banana")
        make_product(category=cat, name="Apple", slug="apple")
        names = list(Product.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Apple", "Banana"])

    def test_category_protected_from_delete_with_products(self):
        cat = make_category()
        make_product(category=cat)
        with self.assertRaises(ProtectedError):
            cat.delete()


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ProductListViewTests(TestCase):
    def test_list_returns_200(self):
        resp = self.client.get(reverse("products:list"))
        self.assertEqual(resp.status_code, 200)

    def test_list_shows_active_product(self):
        make_product(name="Active Product", slug="active-product")
        resp = self.client.get(reverse("products:list"))
        self.assertContains(resp, "Active Product")

    def test_list_excludes_inactive_product(self):
        make_product(
            name="Hidden Product",
            slug="hidden-product",
            is_active=False
        )
        resp = self.client.get(reverse("products:list"))
        self.assertNotContains(resp, "Hidden Product")

    def test_list_renders_category_as_filter_tab(self):
        make_product(category=make_category(
            name="Nutrition",
            slug="nutrition")
        )
        resp = self.client.get(reverse("products:list"))
        self.assertContains(resp, 'data-filter="nutrition"')

    def test_card_carries_data_category_for_clientside_filter(self):
        cat = make_category(name="Nutrition", slug="nutrition")
        make_product(category=cat, name="Protein", slug="protein")
        resp = self.client.get(reverse("products:list"))
        self.assertContains(resp, 'data-category="nutrition"')

    def test_out_of_stock_card_shows_badge(self):
        make_product(name="Sold Out", slug="sold-out", stock=0)
        resp = self.client.get(reverse("products:list"))
        self.assertContains(resp, "Out of stock")

    def test_empty_state_visible_when_catalog_empty(self):
        resp = self.client.get(reverse("products:list"))
        self.assertContains(resp, "No products yet")
        self.assertNotContains(resp, "data-empty-state hidden")

    def test_empty_state_hidden_when_products_exist(self):
        make_product()
        resp = self.client.get(reverse("products:list"))
        self.assertContains(resp, "data-empty-state hidden")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ProductDetailViewTests(TestCase):
    def test_detail_returns_200_for_active_product(self):
        product = make_product(name="Active Product", slug="active-product")
        resp = self.client.get(product.get_absolute_url())
        self.assertEqual(resp.status_code, 200)

    def test_detail_shows_name_and_price(self):
        product = make_product(name="Kettlebell", price=Decimal("59.00"))
        resp = self.client.get(product.get_absolute_url())
        self.assertContains(resp, "Kettlebell")
        self.assertContains(resp, "$59.00")

    def test_detail_shows_category_name(self):
        cat = make_category(name="Merch", slug="merch")
        product = make_product(category=cat, slug="tee")
        resp = self.client.get(product.get_absolute_url())
        self.assertContains(resp, "Merch")

    def test_detail_404_for_inactive_product(self):
        product = make_product(slug="hidden", is_active=False)
        resp = self.client.get(
            reverse("products:detail", kwargs={"slug": product.slug})
        )
        self.assertEqual(resp.status_code, 404)

    def test_detail_404_for_unknown_slug(self):
        resp = self.client.get(reverse(
            "products:detail",
            kwargs={"slug": "nope"})
        )
        self.assertEqual(resp.status_code, 404)

    def test_in_stock_product_shows_stock_count(self):
        product = make_product(slug="bands", stock=7)
        resp = self.client.get(product.get_absolute_url())
        self.assertContains(resp, "7 in stock")
        self.assertContains(resp, "Add to Cart")

    def test_out_of_stock_product_shows_message(self):
        product = make_product(slug="bands", stock=0)
        resp = self.client.get(product.get_absolute_url())
        self.assertContains(resp, "Currently out of stock")

    def test_add_to_cart_form_posts_to_cart_add_url(self):
        product = make_product(slug="bands")
        resp = self.client.get(product.get_absolute_url())
        self.assertContains(resp, f'action="/cart/add/product/{product.id}/"')


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ProductAdminTests(TestCase):
    """Catalog models are manageable from Django admin."""

    def setUp(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="pw12345!"
        )
        self.client.force_login(admin)

    def test_productcategory_changelist_loads(self):
        resp = self.client.get(
            reverse("admin:products_productcategory_changelist")
        )
        self.assertEqual(resp.status_code, 200)

    def test_product_changelist_loads(self):
        resp = self.client.get(reverse("admin:products_product_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_product_add_form_loads(self):
        resp = self.client.get(reverse("admin:products_product_add"))
        self.assertEqual(resp.status_code, 200)
