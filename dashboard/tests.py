from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from plans.models import Plan, PlanCategory
from subscriptions.models import Subscription

from .models import UserGoal, WorkoutLog
from .services import (
    current_streak,
    latest_logged_plan,
    total_minutes,
    week_start,
    weekly_stats,
)

User = get_user_model()

# Use plain static storage in tests so rendering pages that call {% static %}
# does not depend on `collectstatic` having built the manifest first.
SIMPLE_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


def monday_of_current_week():
    today = timezone.localdate()
    return today - timedelta(days=today.weekday())


def make_user(email="u@example.com", **kwargs):
    return User.objects.create_user(email=email, password="pw12345!", **kwargs)


def make_plan(**kwargs):
    category = kwargs.pop("category", None) or PlanCategory.objects.create(
        name="Exercise", slug="exercise"
    )
    defaults = {
        "category": category,
        "title": "Kettlebell Basics",
        "description": "Swing things.",
        "price": "19.00",
    }
    defaults.update(kwargs)
    return Plan.objects.create(**defaults)


class WorkoutLogModelTests(TestCase):
    def test_str_shows_user_and_date(self):
        log = WorkoutLog.objects.create(
            user=make_user(), date=date(2026, 7, 1), duration_minutes=30
        )
        self.assertIn("u@example.com", str(log))
        self.assertIn("2026-07-01", str(log))

    def test_ordering_newest_date_first(self):
        user = make_user()
        older = WorkoutLog.objects.create(
            user=user, date=date(2026, 6, 29), duration_minutes=20
        )
        newer = WorkoutLog.objects.create(
            user=user, date=date(2026, 7, 1), duration_minutes=45
        )
        self.assertEqual(list(WorkoutLog.objects.all()), [newer, older])

    def test_plan_is_optional_and_nulled_when_plan_deleted(self):
        # US-20: log captures plan (optional); history must survive plan removal.
        plan = make_plan()
        log = WorkoutLog.objects.create(
            user=make_user(), plan=plan, date=date(2026, 7, 1), duration_minutes=30
        )
        plan.delete()
        log.refresh_from_db()
        self.assertIsNone(log.plan)


class UserGoalModelTests(TestCase):
    def test_str_shows_user_and_target(self):
        goal = UserGoal.objects.create(
            user=make_user(), weekly_workouts_target=4, week_start=date(2026, 6, 29)
        )
        self.assertIn("u@example.com", str(goal))
        self.assertIn("4", str(goal))

    def test_one_goal_per_user(self):
        # US-21: "Create or update USER_GOAL record for the user" — one row per user.
        user = make_user()
        UserGoal.objects.create(
            user=user, weekly_workouts_target=4, week_start=date(2026, 6, 29)
        )
        with self.assertRaises(IntegrityError):
            UserGoal.objects.create(
                user=user, weekly_workouts_target=5, week_start=date(2026, 6, 29)
            )


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class SetGoalViewTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_login_required(self):
        resp = self.client.get(reverse("dashboard:set_goal"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/accounts/login/"))

    def test_get_shows_form(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:set_goal"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "weekly_workouts_target")

    def test_get_prefills_existing_target(self):
        UserGoal.objects.create(
            user=self.user, weekly_workouts_target=3, week_start=date(2026, 6, 29)
        )
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:set_goal"))
        self.assertContains(resp, 'value="3"')

    def test_post_creates_goal_with_current_week_start(self):
        # US-21: goal saved to USER_GOAL; week_start = Monday of the current week.
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("dashboard:set_goal"), {"weekly_workouts_target": 4}
        )
        self.assertRedirects(resp, reverse("dashboard:home"))
        goal = UserGoal.objects.get(user=self.user)
        self.assertEqual(goal.weekly_workouts_target, 4)
        self.assertEqual(goal.week_start, monday_of_current_week())

    def test_post_updates_existing_goal(self):
        UserGoal.objects.create(
            user=self.user, weekly_workouts_target=3, week_start=date(2020, 1, 6)
        )
        self.client.force_login(self.user)
        self.client.post(reverse("dashboard:set_goal"), {"weekly_workouts_target": 5})
        goals = UserGoal.objects.filter(user=self.user)
        self.assertEqual(goals.count(), 1)
        goal = goals.get()
        self.assertEqual(goal.weekly_workouts_target, 5)
        self.assertEqual(goal.week_start, monday_of_current_week())

    def test_post_zero_target_rejected(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("dashboard:set_goal"), {"weekly_workouts_target": 0}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "field-error")
        self.assertFalse(UserGoal.objects.filter(user=self.user).exists())


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class LogWorkoutViewTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_login_required(self):
        resp = self.client.get(reverse("dashboard:log_workout"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/accounts/login/"))

    def test_get_shows_form(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:log_workout"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "duration_minutes")
        self.assertContains(resp, "plan")
        self.assertContains(resp, "date")

    def test_post_creates_log_linked_to_user_and_plan(self):
        # US-20: log captures plan (optional), date, duration in minutes.
        plan = make_plan()
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("dashboard:log_workout"),
            {
                "plan": plan.id,
                "date": timezone.localdate().isoformat(),
                "duration_minutes": 45,
            },
        )
        self.assertRedirects(resp, reverse("dashboard:home"))
        log = WorkoutLog.objects.get(user=self.user)
        self.assertEqual(log.plan, plan)
        self.assertEqual(log.duration_minutes, 45)

    def test_post_without_plan_is_allowed(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("dashboard:log_workout"),
            {"plan": "", "date": timezone.localdate().isoformat(), "duration_minutes": 30},
        )
        log = WorkoutLog.objects.get(user=self.user)
        self.assertIsNone(log.plan)

    def test_success_message_shown(self):
        # US-38: success toast after "workout logged".
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("dashboard:log_workout"),
            {"plan": "", "date": timezone.localdate().isoformat(), "duration_minutes": 30},
            follow=True,
        )
        self.assertContains(resp, "Workout logged")

    def test_future_date_rejected(self):
        self.client.force_login(self.user)
        tomorrow = timezone.localdate() + timedelta(days=1)
        resp = self.client.post(
            reverse("dashboard:log_workout"),
            {"plan": "", "date": tomorrow.isoformat(), "duration_minutes": 30},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "field-error")
        self.assertFalse(WorkoutLog.objects.exists())

    def test_zero_duration_rejected(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("dashboard:log_workout"),
            {"plan": "", "date": timezone.localdate().isoformat(), "duration_minutes": 0},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(WorkoutLog.objects.exists())

    def test_inactive_plan_not_selectable(self):
        inactive = make_plan(title="Retired Plan", is_active=False)
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("dashboard:log_workout"),
            {
                "plan": inactive.id,
                "date": timezone.localdate().isoformat(),
                "duration_minutes": 30,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(WorkoutLog.objects.exists())


class ServicesTests(TestCase):
    """Unit tests for the dashboard stats helpers (US-19)."""

    def setUp(self):
        self.user = make_user()
        self.today = date(2026, 7, 2)  # a Thursday

    def log(self, day, minutes=30, user=None, plan=None):
        return WorkoutLog.objects.create(
            user=user or self.user, plan=plan, date=day, duration_minutes=minutes
        )

    def test_week_start_returns_monday(self):
        self.assertEqual(week_start(date(2026, 7, 2)), date(2026, 6, 29))
        self.assertEqual(week_start(date(2026, 6, 29)), date(2026, 6, 29))  # Monday
        self.assertEqual(week_start(date(2026, 7, 5)), date(2026, 6, 29))  # Sunday

    def test_streak_zero_without_logs_today_or_yesterday(self):
        self.assertEqual(current_streak(self.user, self.today), 0)
        self.log(self.today - timedelta(days=2))
        self.assertEqual(current_streak(self.user, self.today), 0)

    def test_streak_counts_consecutive_days_including_today(self):
        for offset in (0, 1, 2):
            self.log(self.today - timedelta(days=offset))
        self.assertEqual(current_streak(self.user, self.today), 3)

    def test_streak_may_start_yesterday(self):
        # No workout yet today — yesterday's run still counts.
        self.log(self.today - timedelta(days=1))
        self.log(self.today - timedelta(days=2))
        self.assertEqual(current_streak(self.user, self.today), 2)

    def test_streak_broken_by_gap(self):
        self.log(self.today)
        self.log(self.today - timedelta(days=2))
        self.assertEqual(current_streak(self.user, self.today), 1)

    def test_streak_counts_a_day_once(self):
        self.log(self.today, minutes=20)
        self.log(self.today, minutes=40)
        self.assertEqual(current_streak(self.user, self.today), 1)

    def test_weekly_stats_counts_only_current_week(self):
        self.log(date(2026, 6, 28), minutes=60)  # Sunday of the previous week
        self.log(date(2026, 6, 29), minutes=30)  # Monday boundary
        self.log(self.today, minutes=45)
        stats = weekly_stats(self.user, self.today)
        self.assertEqual(stats["workouts"], 2)
        self.assertEqual(stats["minutes"], 75)

    def test_weekly_stats_completion_against_goal(self):
        UserGoal.objects.create(
            user=self.user, weekly_workouts_target=4, week_start=date(2026, 6, 29)
        )
        self.log(self.today)
        self.log(self.today - timedelta(days=1))
        stats = weekly_stats(self.user, self.today)
        self.assertEqual(stats["target"], 4)
        self.assertEqual(stats["completion"], 50)

    def test_weekly_stats_completion_capped_at_100(self):
        UserGoal.objects.create(
            user=self.user, weekly_workouts_target=2, week_start=date(2026, 6, 29)
        )
        for offset in (0, 1, 2):
            self.log(self.today - timedelta(days=offset))
        self.assertEqual(weekly_stats(self.user, self.today)["completion"], 100)

    def test_weekly_stats_without_goal(self):
        self.log(self.today)
        stats = weekly_stats(self.user, self.today)
        self.assertIsNone(stats["target"])
        self.assertEqual(stats["completion"], 0)

    def test_total_minutes_sums_all_time(self):
        self.log(date(2025, 1, 1), minutes=100)
        self.log(self.today, minutes=30)
        self.assertEqual(total_minutes(self.user), 130)

    def test_total_minutes_zero_without_logs(self):
        self.assertEqual(total_minutes(self.user), 0)

    def test_latest_logged_plan_prefers_most_recent_with_plan(self):
        self.assertIsNone(latest_logged_plan(self.user))
        plan_a = make_plan(title="Plan A")
        plan_b = make_plan(title="Plan B", category=plan_a.category)
        self.log(date(2026, 6, 20), plan=plan_a)
        self.log(date(2026, 6, 25), plan=plan_b)
        self.log(self.today)  # planless log should not hide plan_b
        self.assertEqual(latest_logged_plan(self.user), plan_b)

    def test_stats_are_scoped_to_user(self):
        other = make_user("other@example.com")
        self.log(self.today, minutes=99, user=other)
        self.assertEqual(weekly_stats(self.user, self.today)["workouts"], 0)
        self.assertEqual(total_minutes(self.user), 0)
        self.assertEqual(current_streak(self.user, self.today), 0)


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = make_user(first_name="Andreas")

    def test_login_required(self):
        resp = self.client.get(reverse("dashboard:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/accounts/login/"))

    def test_welcome_header_with_free_chip_linking_to_manage(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:home"))
        self.assertContains(resp, "Welcome back, Andreas")
        self.assertContains(resp, "Free")
        self.assertContains(resp, reverse("subscriptions:manage"))

    def test_stat_tiles_show_workouts_minutes_streak_completion(self):
        # US-19: weekly workouts completed, total minutes logged, streak, goal %.
        UserGoal.objects.create(
            user=self.user,
            weekly_workouts_target=5,
            week_start=monday_of_current_week(),
        )
        today = timezone.localdate()
        WorkoutLog.objects.create(user=self.user, date=today, duration_minutes=30)
        WorkoutLog.objects.create(user=self.user, date=today, duration_minutes=45)
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:home"))
        self.assertContains(resp, '<div class="stat-tile__value">2</div>', html=True)
        self.assertContains(resp, '<div class="stat-tile__value">75</div>', html=True)
        self.assertContains(resp, '<div class="stat-tile__value">1</div>', html=True)
        self.assertContains(resp, '<div class="stat-tile__value">40%</div>', html=True)
        self.assertContains(resp, "2 / 5")

    def test_upsell_card_for_free_user_only(self):
        # US-19: free users see an "Upgrade to Premium" upsell card.
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse("dashboard:home")), "Go Premium")
        Subscription.objects.create(
            user=self.user,
            stripe_subscription_id="sub_test_1",
            stripe_customer_id="cus_test_1",
            status="active",
        )
        self.assertNotContains(
            self.client.get(reverse("dashboard:home")), "Go Premium"
        )

    def test_todays_plan_empty_state(self):
        # US-19: "No workout scheduled" empty state with a Browse Plans CTA.
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:home"))
        self.assertContains(resp, "No workout scheduled")
        self.assertContains(resp, "Browse Plans")

    def test_todays_plan_shows_latest_logged_plan(self):
        plan = make_plan(title="Hypertrophy Block")
        WorkoutLog.objects.create(
            user=self.user, plan=plan, date=timezone.localdate(), duration_minutes=30
        )
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:home"))
        self.assertContains(resp, "Hypertrophy Block")
        self.assertContains(resp, plan.get_absolute_url())
        self.assertNotContains(resp, "No workout scheduled")

    def test_quick_actions_and_community_card(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:home"))
        self.assertContains(resp, reverse("dashboard:log_workout"))
        self.assertContains(resp, reverse("dashboard:set_goal"))
        self.assertContains(resp, reverse("community:feed"))
        self.assertContains(resp, "View Feed")

    def test_without_goal_prompts_to_set_one(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("dashboard:home"))
        self.assertContains(resp, "Set your weekly goal")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class DashboardAdminTests(TestCase):
    """Sprint 5: workout logs and goals are manageable from Django admin."""

    def setUp(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="pw12345!"
        )
        self.client.force_login(admin)

    def test_workoutlog_changelist_loads(self):
        resp = self.client.get(reverse("admin:dashboard_workoutlog_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_usergoal_changelist_loads(self):
        resp = self.client.get(reverse("admin:dashboard_usergoal_changelist"))
        self.assertEqual(resp.status_code, 200)
