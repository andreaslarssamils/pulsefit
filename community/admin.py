from django.contrib import admin

from .models import CommunityPost


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "snippet")
    list_filter = ("created_at",)
    search_fields = ("user__email", "body")

    @admin.display(description="Post")
    def snippet(self, obj):
        return obj.body[:60]
