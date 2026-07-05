from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BlogPost

User = get_user_model()

# Use plain static storage in tests so rendering pages that call {% static %}
# does not depend on `collectstatic` having built the manifest first.
SIMPLE_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


def make_user(email="author@example.com", **kwargs):
    return User.objects.create_user(email=email, password="pw12345!", **kwargs)


def make_post(title="Hello World", status="published", **kwargs):
    kwargs.setdefault("body", "Body text here.")
    return BlogPost.objects.create(title=title, status=status, **kwargs)


class BlogPostModelTests(TestCase):
    def test_slug_auto_populated_from_title(self):
        # slug-based URL; mirrors Plan/Product auto-slug in save().
        post = make_post(title="Ten Training Tips")
        self.assertEqual(post.slug, "ten-training-tips")

    def test_publishing_stamps_published_at(self):
        # published posts order by publish time.
        post = make_post(status="published")
        self.assertIsNotNone(post.published_at)

    def test_draft_has_no_published_at(self):
        self.assertIsNone(make_post(status="draft").published_at)

    def test_get_absolute_url_uses_slug(self):
        post = make_post(title="My Post")
        self.assertEqual(post.get_absolute_url(), f"/blog/{post.slug}/")

    def test_ordering_reverse_chronological(self):
        older = make_post(title="Older")
        newer = make_post(title="Newer")
        self.assertEqual(list(BlogPost.objects.all()), [newer, older])


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class BlogListViewTests(TestCase):
    def test_list_is_public(self):
        # blog is readable without signing in.
        self.assertEqual(
            self.client.get(
                reverse("blog:list")).status_code,
            200)

    def test_only_published_shown(self):
        make_post(title="Published Post", status="published")
        make_post(title="Secret Draft", status="draft")
        resp = self.client.get(reverse("blog:list"))
        self.assertContains(resp, "Published Post")
        self.assertNotContains(resp, "Secret Draft")

    def test_reverse_chronological(self):
        make_post(title="Older Article", status="published")
        make_post(title="Newer Article", status="published")
        content = self.client.get(reverse("blog:list")).content.decode()
        self.assertLess(
            content.index("Newer Article"),
            content.index("Older Article"))

    def test_excerpt_shown_on_card(self):
        make_post(
            title="Has Excerpt",
            status="published",
            excerpt="A short teaser")
        self.assertContains(
            self.client.get(
                reverse("blog:list")),
            "A short teaser")

    def test_empty_state(self):
        self.assertContains(
            self.client.get(
                reverse("blog:list")),
            "No posts yet")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class BlogDetailViewTests(TestCase):
    def test_published_detail_renders(self):
        #  detail shows title, body, author, date.
        author = make_user(first_name="Nora", last_name="Falk")
        post = make_post(
            title="Deep Dive", status="published", author=author,
            body="Full article body",
        )
        resp = self.client.get(post.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Deep Dive")
        self.assertContains(resp, "Full article body")
        self.assertContains(resp, "Nora Falk")

    def test_draft_detail_404(self):
        # only published posts are visible.
        post = make_post(title="Not Yet", status="draft")
        self.assertEqual(
            self.client.get(
                post.get_absolute_url()).status_code,
            404)


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class BlogAdminTests(TestCase):
    """ BlogPost is managed from the Django admin."""

    def setUp(self):
        admin = User.objects.create_superuser(
            email="admin@example.com", password="pw12345!"
        )
        self.client.force_login(admin)

    def test_changelist_loads(self):
        resp = self.client.get(reverse("admin:blog_blogpost_changelist"))
        self.assertEqual(resp.status_code, 200)
