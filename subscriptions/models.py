from django.conf import settings
from django.db import models


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("trialing", "Trialing"),
        ("past_due", "Past due"),
        ("canceled", "Canceled"),
        ("unpaid", "Unpaid"),
        ("incomplete", "Incomplete"),
        ("incomplete_expired", "Incomplete expired"),
    ]
    ACCESS_GRANTING = {"active", "trialing", "past_due"}

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription")
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    stripe_customer_id = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES)
    plan_tier = models.CharField(max_length=20, default="premium")
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — {self.status}"

    @property
    def is_active(self):
        return self.status in self.ACCESS_GRANTING
