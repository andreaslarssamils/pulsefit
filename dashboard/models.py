from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class WorkoutLog(models.Model):
    """A completed workout logged by a user (US-20)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workout_logs")
    plan = models.ForeignKey(
        "plans.Plan",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="workout_logs",
    )
    date = models.DateField()
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.user} — {self.date} ({self.duration_minutes} min)"


class UserGoal(models.Model):
    """A user's weekly workout target shown on the dashboard (US-21).

    One row per user.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goal"
    )
    weekly_workouts_target = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)]
    )
    week_start = models.DateField()

    def __str__(self):
        return f"{self.user}: {self.weekly_workouts_target}/week"
