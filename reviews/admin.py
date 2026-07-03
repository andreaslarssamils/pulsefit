from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """ """
    list_display = ("user", "target", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__email", "body")
    readonly_fields = ("created_at", "updated_at")
