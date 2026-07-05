from django import forms
from django.utils import timezone

from plans.models import Plan

from .models import UserGoal, WorkoutLog


class GoalForm(forms.ModelForm):
    """Weekly workout target form (US-21)."""

    class Meta:
        model = UserGoal
        fields = ["weekly_workouts_target"]
        labels = {"weekly_workouts_target": "Workouts per week"}


class WorkoutLogForm(forms.ModelForm):
    """Log a completed workout (US-20)."""

    class Meta:
        model = WorkoutLog
        fields = ["plan", "date", "duration_minutes"]
        labels = {
            "plan": "Plan (optional)",
            "date": "Date",
            "duration_minutes": "Duration (minutes)",
        }
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = Plan.objects.filter(is_active=True)
        self.fields["plan"].empty_label = "No plan"
        self.fields["date"].initial = timezone.localdate

    def clean_date(self):
        day = self.cleaned_data["date"]
        if day > timezone.localdate():
            raise forms.ValidationError(
                "Workout date cannot be in the future.")
        return day
