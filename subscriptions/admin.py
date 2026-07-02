from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "plan_tier",
        "current_period_end",
        "cancel_at_period_end",
    )
    list_filter = ("status", "plan_tier", "cancel_at_period_end")
    search_fields = ("user__email", "stripe_subscription_id", "stripe_customer_id")
    readonly_fields = ("created_at", "updated_at")
