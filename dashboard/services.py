"""Dashboard statistics helpers (US-19/US-20/US-21). Weeks run Monday–Sunday."""

from datetime import timedelta

from django.db.models import Sum

from .models import UserGoal


def week_start(day):
    """Return the Monday of the week containing `day`."""
    return day - timedelta(days=day.weekday())


def weekly_stats(user, today):
    """Workouts, minutes and goal completion for the week containing `today`."""
    monday = week_start(today)
    logs = user.workout_logs.filter(date__range=(monday, monday + timedelta(days=6)))
    workouts = logs.count()
    minutes = logs.aggregate(total=Sum("duration_minutes"))["total"] or 0
    goal = UserGoal.objects.filter(user=user).first()
    target = goal.weekly_workouts_target if goal else None
    completion = min(100, round(workouts / target * 100)) if target else 0
    return {
        "workouts": workouts,
        "minutes": minutes,
        "target": target,
        "completion": completion,
    }


def total_minutes(user):
    """All-time minutes logged (the "total minutes" stat tile)."""
    return user.workout_logs.aggregate(total=Sum("duration_minutes"))["total"] or 0


def current_streak(user, today):
    """Consecutive days with at least one workout, ending today or yesterday."""
    days = set(user.workout_logs.filter(date__lte=today).values_list("date", flat=True))
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def latest_logged_plan(user):
    """The plan on the user's most recent plan-linked workout ("Today's Plan")."""
    log = user.workout_logs.filter(plan__isnull=False).select_related("plan").first()
    return log.plan if log else None
