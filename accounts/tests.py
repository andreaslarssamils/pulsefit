from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()

SIMPLE_STATIC_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class CustomUserModelTests(TestCase):
    """Tests for the CustomUser model and its manager."""
    def test_email_is_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_create_user_with_email(self):
        """Test creating a regular user with an email address."""
        user = User.objects.create_user(email="a@example.com", password="pw12345!")
        self.assertEqual(user.email, "a@example.com")
        self.assertTrue(user.check_password("pw12345!"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Test creating a superuser with an email address."""
        admin = User.objects.create_superuser(
            email="admin@example.com", password="pw12345!"
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_create_user_without_email_raises(self):
        """Test that creating a user without an email raises a ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pw12345!")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class AuthFlowTests(TestCase):
    """Tests for the authentication flow, including signup, login, and logout."""
    def test_signup_creates_user_logs_in_and_maps_full_name(self):
        """Test that signing up creates a user, logs them in, and maps the full name to first and last names."""
        resp = self.client.post(
            reverse("account_signup"),
            {
                "name": "Andreas Larsson",
                "email": "new@example.com",
                "password1": "SuperSecret123!",
                "password2": "SuperSecret123!",
            },
        )
        self.assertEqual(resp.status_code, 302)  # auto sign-in -> redirect (US-01)

        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.first_name, "Andreas")
        self.assertEqual(user.last_name, "Larsson")
        self.assertIn("_auth_user_id", self.client.session)  # signed in

    def test_login_with_wrong_password_shows_non_specific_error(self):
        """Test that logging in with the wrong password does not reveal whether the email exists."""
        User.objects.create_user(email="u@example.com", password="rightpass123!")
        resp = self.client.post(
            reverse("account_login"),
            {"login": "u@example.com", "password": "wrongpass"},
        )
        # Re-renders the form (200) instead of redirecting; user stays anonymous.
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        # US-02: the error must not reveal whether the email exists.
        self.assertContains(resp, "are not correct")

    def test_signup_with_duplicate_email_is_rejected(self):
        """Test that signing up with an email that already exists is rejected."""
        User.objects.create_user(email="taken@example.com", password="RightPass123!")
        resp = self.client.post(
            reverse("account_signup"),
            {
                "name": "Someone Else",
                "email": "taken@example.com",
                "password1": "AnotherPass123!",
                "password2": "AnotherPass123!",
            },
        )
        # US-01: duplicate email re-renders with an error; no second user created.
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(email="taken@example.com").count(), 1)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_success_redirects(self):
        """Test that logging in with correct credentials redirects and logs the user in."""
        User.objects.create_user(email="ok@example.com", password="rightpass123!")
        resp = self.client.post(
            reverse("account_login"),
            {"login": "ok@example.com", "password": "rightpass123!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_logout_redirects(self):
        """Test that logging out redirects and logs the user out."""
        user = User.objects.create_user(
            email="bye@example.com", password="rightpass123!"
        )
        self.client.force_login(user)
        resp = self.client.post(reverse("account_logout"))
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)


class StripeCustomerFieldTests(TestCase):
    """Tests for the stripe_customer_id field in the CustomUser model."""
    def test_new_user_has_blank_stripe_customer_id(self):
        user = User.objects.create_user(email="s@example.com", password="pw12345!")
        self.assertEqual(user.stripe_customer_id, "")
