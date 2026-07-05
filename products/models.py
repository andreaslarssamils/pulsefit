from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class ProductCategory(models.Model):
    """Grouping for products (e.g. Exercise,
    Nutrition, Merch); drives shop filter tabs.
    """

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "product categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    """A shop product shown in the catalog """

    category = models.ForeignKey(
        ProductCategory, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField()
    image = models.URLField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    # Digital products (downloads) skip shipping-address collection at
    # checkout.
    is_digital = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def in_stock(self):
        return self.stock > 0

    def save(self, *args, **kwargs):
        # prepopulated_fields only fills the slug in the admin; do it here
        # too so
        # seeded/programmatic rows get a slug.
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"slug": self.slug})
