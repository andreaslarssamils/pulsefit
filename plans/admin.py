from django.contrib import admin

from .models import Plan, PlanCategory


@admin.register(PlanCategory)
class PlanCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price", "premium_only", "is_active")
    list_filter = ("category", "premium_only", "is_active")
    search_fields = ("title", "description")
    list_editable = ("is_active",)
    prepopulated_fields = {"slug": ("title",)}
