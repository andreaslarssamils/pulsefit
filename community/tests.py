from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CommunityPost

User = get_user_model()

# Use plain static storage in tests so rendering pages that call {% static %}
# does not depend on `collectstatic` having built the manifest first.
SIMPLE_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


def make_user(email="member@example.com", **kwargs):
    return User.objects.create_user(email=email, password="pw12345!", **kwargs)


class CommunityPostModelTests(TestCase):
    def test_str_shows_author_and_snippet(self):
        post = CommunityPost.objects.create(
            user=make_user(), body="Crushed leg day, new squat PR!"
        )
        self.assertIn("member@example.com", str(post))
        self.assertIn("Crushed leg day", str(post))

    def test_ordering_reverse_chronological(self):
        # US-22: posts are shown in reverse chronological order.
        user = make_user()
        first = CommunityPost.objects.create(user=user, body="First post")
        second = CommunityPost.objects.create(user=user, body="Second post")
        self.assertEqual(list(CommunityPost.objects.all()), [second, first])


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class FeedViewTests(TestCase):
    def test_feed_is_public(self):
        # US-22: community feed is publicly visible (read-only for visitors).
        resp = self.client.get(reverse("community:feed"))
        self.assertEqual(resp.status_code, 200)

    def test_posts_listed_newest_first(self):
        user = make_user()
        CommunityPost.objects.create(user=user, body="Older update")
        CommunityPost.objects.create(user=user, body="Fresh update")
        resp = self.client.get(reverse("community:feed"))
        content = resp.content.decode()
        self.assertLess(
            content.index("Fresh update"),
            content.index("Older update"))

    def test_post_shows_author_name_and_timestamp(self):
        user = make_user(first_name="Anna", last_name="Berg")
        post = CommunityPost.objects.create(user=user, body="New deadlift PR!")
        resp = self.client.get(reverse("community:feed"))
        self.assertContains(resp, "Anna Berg")
        self.assertContains(resp, "New deadlift PR!")
        self.assertContains(resp, str(post.created_at.year))

    def test_author_without_name_falls_back_to_email(self):
        user = make_user()
        CommunityPost.objects.create(user=user, body="Hello!")
        resp = self.client.get(reverse("community:feed"))
        self.assertContains(resp, "member@example.com")

    def test_visitor_sees_join_cta(self):
        # US-22: visitors see a "Join Free" CTA to encourage sign-up.
        resp = self.client.get(reverse("community:feed"))
        self.assertContains(resp, "Join the PulseFit community")

    def test_member_does_not_see_join_cta(self):
        self.client.force_login(make_user())
        resp = self.client.get(reverse("community:feed"))
        self.assertNotContains(resp, "Join the PulseFit community")

    def test_empty_state_when_no_posts(self):
        resp = self.client.get(reverse("community:feed"))
        self.assertContains(resp, "No posts yet")

    def test_visitor_does_not_see_composer(self):
        # US-23: post form is visible only to signed-in users.
        resp = self.client.get(reverse("community:feed"))
        self.assertNotContains(resp, 'name="body"')

    def test_member_sees_composer(self):
        self.client.force_login(make_user())
        resp = self.client.get(reverse("community:feed"))
        self.assertContains(resp, 'name="body"')

    def test_stats_tiles_show_counts(self):
        anna = make_user(email="anna@example.com")
        bjorn = make_user(email="bjorn@example.com")
        CommunityPost.objects.create(user=anna, body="One")
        CommunityPost.objects.create(user=anna, body="Two")
        CommunityPost.objects.create(user=bjorn, body="Three")
        resp = self.client.get(reverse("community:feed"))
        self.assertContains(
            resp,
            '<div class="stat-tile__value">2</div>',
            html=True)
        self.assertContains(
            resp,
            '<div class="stat-tile__value">3</div>',
            html=True)
        self.assertContains(resp, "Members")
        self.assertContains(resp, "Posts")
        self.assertContains(resp, "New this week")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class PostCreateViewTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_login_required(self):
        resp = self.client.post(
            reverse("community:post_create"), {"body": "Sneaky visitor post"}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/accounts/login/"))
        self.assertFalse(CommunityPost.objects.exists())

    def test_post_creates_linked_to_user_with_message(self):
        # US-23: post is associated with request.user; success message on
        # redirect.
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("community:post_create"), {
                "body": "First 10k done!"}, follow=True)
        self.assertRedirects(resp, reverse("community:feed"))
        post = CommunityPost.objects.get()
        self.assertEqual(post.user, self.user)
        self.assertEqual(post.body, "First 10k done!")
        self.assertContains(resp, "shared")

    def test_new_post_appears_at_top_of_feed(self):
        # US-23: after posting, the new post appears at the top of the feed.
        CommunityPost.objects.create(
            user=make_user("old@example.com"),
            body="Old news")
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("community:post_create"), {
                "body": "Hot off the press"}, follow=True)
        content = resp.content.decode()
        self.assertLess(
            content.index("Hot off the press"),
            content.index("Old news"))

    def test_empty_body_rejected(self):
        # US-23: post requires a non-empty body.
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("community:post_create"), {
                "body": "   "})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "field-error")
        self.assertFalse(CommunityPost.objects.exists())


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class PostDeleteViewTests(TestCase):
    def setUp(self):
        self.author = make_user("author@example.com")
        self.post = CommunityPost.objects.create(
            user=self.author, body="My own post")
        self.delete_url = reverse(
            "community:post_delete", kwargs={
                "pk": self.post.pk})

    def test_login_required(self):
        resp = self.client.get(self.delete_url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].startswith("/accounts/login/"))

    def test_delete_button_visible_only_to_author(self):
        # US-24: delete button is visible only to the post author.
        self.client.force_login(self.author)
        self.assertContains(
            self.client.get(
                reverse("community:feed")),
            self.delete_url)

        self.client.force_login(make_user("other@example.com"))
        self.assertNotContains(
            self.client.get(reverse("community:feed")), self.delete_url
        )

    def test_get_shows_confirmation(self):
        # US-24: confirmation is required before deletion.
        self.client.force_login(self.author)
        resp = self.client.get(self.delete_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Delete this post?")
        self.assertTrue(CommunityPost.objects.filter(pk=self.post.pk).exists())

    def test_post_deletes_and_redirects_with_message(self):
        self.client.force_login(self.author)
        resp = self.client.post(self.delete_url, follow=True)
        self.assertRedirects(resp, reverse("community:feed"))
        self.assertFalse(
            CommunityPost.objects.filter(
                pk=self.post.pk).exists())
        self.assertContains(resp, "deleted")

    def test_other_user_gets_404(self):
        self.client.force_login(make_user("other@example.com"))
        self.assertEqual(self.client.get(self.delete_url).status_code, 404)
        self.assertEqual(self.client.post(self.delete_url).status_code, 404)
        self.assertTrue(CommunityPost.objects.filter(pk=self.post.pk).exists())


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class CommunityAdminTests(TestCase):
    """Sprint 5: community posts are manageable from Django admin."""

    def setUp(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="pw12345!"
        )
        self.client.force_login(admin)

    def test_communitypost_changelist_loads(self):
        resp = self.client.get(
            reverse("admin:community_communitypost_changelist"))
        self.assertEqual(resp.status_code, 200)
