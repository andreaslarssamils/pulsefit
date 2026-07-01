import uuid

from django.conf import settings
from django.db import models


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("shipped", "Shipped"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total = models.DecimalField(max_digits=9, decimal_places=2)
    shipping_name = models.CharField(max_length=200, blank=True)
    shipping_address_line1 = models.CharField(max_length=200, blank=True)
    shipping_address_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=120, blank=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=2, blank=True)
    stripe_checkout_session_id = models.CharField(
        max_length=200, unique=True, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    @staticmethod
    def generate_order_number():
        return f"PF-{uuid.uuid4().hex[:8].upper()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    plan = models.ForeignKey(
        "plans.Plan", on_delete=models.PROTECT, null=True, blank=True
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.PROTECT, null=True, blank=True
    )
    name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(plan__isnull=False, product__isnull=True)
                    | models.Q(plan__isnull=True, product__isnull=False)
                ),
                name="orderitem_exactly_one_of_plan_or_product",
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
