from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """
        Inline admin interface for OrderItem model.
    """
    model = OrderItem
    extra = 0
    readonly_fields = ("name", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "total", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("order_number", "user__email")
    list_editable = ("status",)
    inlines = [OrderItemInline]
