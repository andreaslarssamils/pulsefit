from django.contrib import admin

from .models import Plan, PlanAccess, PlanCategory


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


@admin.register(PlanAccess)
class PlanAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "source", "created_at")
    list_filter = ("source",)
    search_fields = ("user__email", "plan__title")
