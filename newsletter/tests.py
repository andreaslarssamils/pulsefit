from unittest.mock import patch

import requests
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .services import AlreadySubscribed, NewsletterError, subscribe_email

MAILCHIMP = dict(
    MAILCHIMP_API_KEY="key-us1",
    MAILCHIMP_AUDIENCE_ID="aud123",
    MAILCHIMP_SERVER_PREFIX="us1",
)

VIEW_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(**MAILCHIMP)
class SubscribeEmailTests(SimpleTestCase):
    @patch("newsletter.services.requests.post")
    def test_success_posts_expected_payload(self, mock_post):
        mock_post.return_value.status_code = 200
        self.assertIsNone(subscribe_email("a@b.com"))
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(
            args[0],
            "https://us1.api.mailchimp.com/3.0/lists/aud123/members",
        )
        self.assertEqual(kwargs["auth"], ("anystring", "key-us1"))
        self.assertEqual(
            kwargs["json"], {"email_address": "a@b.com", "status": "subscribed"}
        )

    @patch("newsletter.services.requests.post")
    def test_member_exists_raises_already_subscribed(self, mock_post):
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {"title": "Member Exists"}
        with self.assertRaises(AlreadySubscribed):
            subscribe_email("a@b.com")

    @patch("newsletter.services.requests.post")
    def test_other_error_raises_newsletter_error(self, mock_post):
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "boom"
        with self.assertRaises(NewsletterError):
            subscribe_email("a@b.com")

    @patch("newsletter.services.requests.post")
    def test_network_error_raises_newsletter_error(self, mock_post):
        mock_post.side_effect = requests.RequestException("down")
        with self.assertRaises(NewsletterError):
            subscribe_email("a@b.com")


class SubscribeEmailUnconfiguredTests(SimpleTestCase):
    @override_settings(
        MAILCHIMP_API_KEY="", MAILCHIMP_AUDIENCE_ID="", MAILCHIMP_SERVER_PREFIX=""
    )
    @patch("newsletter.services.requests.post")
    def test_missing_config_raises_without_calling_mailchimp(self, mock_post):
        with self.assertRaises(NewsletterError):
            subscribe_email("a@b.com")
        mock_post.assert_not_called()


@override_settings(STORAGES=VIEW_STATIC_STORAGES)
class SubscribeViewTests(TestCase):
    def test_get_not_allowed(self):
        self.assertEqual(
            self.client.get(reverse("newsletter:subscribe")).status_code, 405
        )

    @patch("newsletter.views.subscribe_email")
    def test_valid_email_subscribes(self, mock_sub):
        resp = self.client.post(
            reverse("newsletter:subscribe"),
            {"email": "a@b.com"},
            HTTP_REFERER="/",
            follow=True,
        )
        mock_sub.assert_called_once_with("a@b.com")
        self.assertContains(resp, "Check your inbox for fitness tips")

    @patch("newsletter.views.subscribe_email")
    def test_invalid_email_does_not_call_service(self, mock_sub):
        resp = self.client.post(
            reverse("newsletter:subscribe"),
            {"email": "not-an-email"},
            HTTP_REFERER="/",
            follow=True,
        )
        mock_sub.assert_not_called()
        self.assertContains(resp, "valid email")

    @patch("newsletter.views.subscribe_email", side_effect=AlreadySubscribed())
    def test_already_subscribed_shows_info(self, mock_sub):
        resp = self.client.post(
            reverse("newsletter:subscribe"),
            {"email": "a@b.com"},
            HTTP_REFERER="/",
            follow=True,
        )
        self.assertContains(resp, "already subscribed")

    @patch("newsletter.views.subscribe_email", side_effect=NewsletterError())
    def test_service_error_shows_error(self, mock_sub):
        resp = self.client.post(
            reverse("newsletter:subscribe"),
            {"email": "a@b.com"},
            HTTP_REFERER="/",
            follow=True,
        )
        self.assertContains(resp, "went wrong")
