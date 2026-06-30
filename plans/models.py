from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class PlanCategory(models.Model):
    """
        Grouping for plans (e.g. Exercise, Nutrition);
        drives the catalog filter tabs.
    """

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "plan categories"

    def __str__(self):
        return self.name


class Plan(models.Model):
    """A training/nutrition plan shown in the catalog."""

    category = models.ForeignKey(
        PlanCategory, on_delete=models.PROTECT, related_name="plans"
    )
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField()
    image = models.URLField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    premium_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """
            prepopulated_fields only fills the slug in the admin; do it here
            too so seeded/programmatic rows get a slug.
        """
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("plans:detail", kwargs={"slug": self.slug})
