import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Challenge

User = get_user_model()

# Plain static storage so page renders don't need a built manifest.
SIMPLE_STATIC_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def make_challenge(
        title="Summer Shred",
        offset_start=-1,
        offset_end=1,
        **kwargs):
    today = timezone.localdate()
    kwargs.setdefault("description", "A group challenge.")
    kwargs.setdefault("is_active", True)
    return Challenge.objects.create(
        title=title,
        start_date=today + datetime.timedelta(days=offset_start),
        end_date=today + datetime.timedelta(days=offset_end),
        **kwargs,
    )


class ChallengeModelTests(TestCase):
    def test_status_active_when_today_in_range(self):
        self.assertEqual(
            make_challenge(
                offset_start=-1,
                offset_end=1).status,
            "active")

    def test_status_active_on_boundary_dates(self):
        self.assertEqual(
            make_challenge(
                offset_start=0,
                offset_end=0).status,
            "active")

    def test_status_upcoming_when_start_in_future(self):
        self.assertEqual(
            make_challenge(offset_start=3, offset_end=10).status, "upcoming"
        )

    def test_status_ended_when_end_in_past(self):
        self.assertEqual(
            make_challenge(offset_start=-10, offset_end=-3).status, "ended"
        )

    def test_ordering_newest_start_first(self):
        old = make_challenge(title="Old", offset_start=-20, offset_end=-10)
        new = make_challenge(title="New", offset_start=-2, offset_end=5)
        self.assertEqual(list(Challenge.objects.all()), [new, old])


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ChallengeAdminTests(TestCase):
    def setUp(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="pw12345!"
        )
        self.client.force_login(admin)

    def test_changelist_loads(self):
        resp = self.client.get(
            reverse("admin:challenges_challenge_changelist"))
        self.assertEqual(resp.status_code, 200)


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ChallengeListViewTests(TestCase):
    def test_list_is_public(self):
        self.assertEqual(
            self.client.get(
                reverse("challenges:list")).status_code,
            200)

    def test_only_active_shown(self):
        make_challenge(title="Live Challenge", is_active=True)
        make_challenge(title="Hidden Challenge", is_active=False)
        resp = self.client.get(reverse("challenges:list"))
        self.assertContains(resp, "Live Challenge")
        self.assertNotContains(resp, "Hidden Challenge")

    def test_active_challenge_shows_status_badge(self):
        make_challenge(title="Ongoing", offset_start=-1, offset_end=5)
        self.assertContains(
            self.client.get(
                reverse("challenges:list")),
            "Active")

    def test_empty_state(self):
        self.assertContains(
            self.client.get(reverse("challenges:list")), "No challenges yet"
        )
