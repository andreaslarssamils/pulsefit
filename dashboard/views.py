from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import GoalForm, WorkoutLogForm
from .models import UserGoal
from .services import (
    current_streak,
    latest_logged_plan,
    total_minutes,
    week_start,
    weekly_stats,
)


@login_required
def dashboard(request):
    """Personal dashboard: stat tiles, weekly progress, today's plan (US-19)."""
    today = timezone.localdate()
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "week": weekly_stats(request.user, today),
            "total_minutes": total_minutes(request.user),
            "streak": current_streak(request.user, today),
            "todays_plan": latest_logged_plan(request.user),
        },
    )


@login_required
def set_goal(request):
    """Create or update the user's weekly workout target (US-21)."""
    goal = UserGoal.objects.filter(user=request.user).first()
    if request.method == "POST":
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.week_start = week_start(timezone.localdate())
            goal.save()
            messages.success(request, "Weekly goal saved.")
            return redirect("dashboard:home")
    else:
        form = GoalForm(instance=goal)
    return render(request, "dashboard/set_goal.html", {"form": form})


@login_required
def log_workout(request):
    """Log a completed workout (US-20)."""
    if request.method == "POST":
        form = WorkoutLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            log.save()
            messages.success(request, "Workout logged. Keep it up!")
            return redirect("dashboard:home")
    else:
        form = WorkoutLogForm()
    return render(request, "dashboard/log_workout.html", {"form": form})
