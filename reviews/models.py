from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    """A 1–5 star review on either a plan or a product (US-28).

    Targets exactly one of plan/product — the same two-nullable-FK +
    CheckConstraint pattern as ``orders.OrderItem``.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    plan = models.ForeignKey(
        "plans.Plan",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reviews",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(plan__isnull=False, product__isnull=True)
                    | models.Q(plan__isnull=True, product__isnull=False)
                ),
                name="review_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["user", "plan"],
                condition=models.Q(plan__isnull=False),
                name="uniq_review_user_plan",
            ),
            models.UniqueConstraint(
                fields=["user", "product"],
                condition=models.Q(product__isnull=False),
                name="uniq_review_user_product",
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.target} ({self.rating}★)"

    @property
    def target(self):
        return self.plan or self.product
