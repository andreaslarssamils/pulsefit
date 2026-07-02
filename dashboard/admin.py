from django.contrib import admin

from .models import UserGoal, WorkoutLog


@admin.register(WorkoutLog)
class WorkoutLogAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "plan", "duration_minutes")
    list_filter = ("date",)
    search_fields = ("user__email", "plan__title")


@admin.register(UserGoal)
class UserGoalAdmin(admin.ModelAdmin):
    list_display = ("user", "weekly_workouts_target", "week_start")
    search_fields = ("user__email",)
