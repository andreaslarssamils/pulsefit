from datetime import datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from plans.models import Plan, PlanAccess, PlanCategory
from subscriptions.models import Subscription
from subscriptions.services import (
    sync_from_stripe_subscription,
    sync_subscription_access,
)

User = get_user_model()

SIMPLE_STATIC_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


def fake_stripe_sub(
    customer_id="cus_1",
    sub_id="sub_1",
    status="active",
    cancel_at_period_end=False,
    period_end=1893456000,
):
    return {
        "id": sub_id,
        "customer": customer_id,
        "status": status,
        "cancel_at_period_end": cancel_at_period_end,
        "items": {"data": [{"current_period_end": period_end}]},
    }


class SubscriptionModelTests(TestCase):
    def _sub(self, status):
        user = User.objects.create_user(
            email=f"{status}@example.com", password="pw12345!"
        )
        return Subscription.objects.create(
            user=user,
            stripe_subscription_id=f"sub_{status}",
            stripe_customer_id="cus_1",
            status=status,
        )

    def test_active_states_grant(self):
        for status in ("active", "trialing", "past_due"):
            self.assertTrue(self._sub(status).is_active, status)

    def test_inactive_states_do_not_grant(self):
        for status in (
            "canceled",
            "unpaid",
            "incomplete",
                "incomplete_expired"):
            self.assertFalse(self._sub(status).is_active, status)


class SyncAccessTests(TestCase):
    def setUp(self):
        self.cat = PlanCategory.objects.create(
            name="Exercise", slug="exercise")
        self.premium = Plan.objects.create(
            category=self.cat,
            title="Elite",
            description="x",
            price="99.00",
            premium_only=True,
        )
        self.free_plan = Plan.objects.create(
            category=self.cat,
            title="Strength",
            description="x",
            price="49.00",
            premium_only=False,
        )
        self.user = User.objects.create_user(
            email="a@example.com", password="pw12345!")
        self.sub = Subscription.objects.create(
            user=self.user,
            stripe_subscription_id="sub_1",
            stripe_customer_id="cus_1",
            status="active",
        )

    def test_active_grants_rows_for_premium_plans_only(self):
        sync_subscription_access(self.sub)
        self.assertTrue(
            PlanAccess.objects.filter(
                user=self.user, plan=self.premium, source="subscription"
            ).exists()
        )
        self.assertFalse(
            PlanAccess.objects.filter(
                user=self.user,
                plan=self.free_plan).exists())

    def test_idempotent(self):
        sync_subscription_access(self.sub)
        sync_subscription_access(self.sub)
        self.assertEqual(PlanAccess.objects.filter(user=self.user).count(), 1)

    def test_inactive_revokes_subscription_rows_but_keeps_purchases(self):
        PlanAccess.objects.create(
            user=self.user, plan=self.premium, source="subscription"
        )
        PlanAccess.objects.create(
            user=self.user, plan=self.free_plan, source="purchase"
        )
        self.sub.status = "canceled"
        sync_subscription_access(self.sub)
        self.assertFalse(
            PlanAccess.objects.filter(
                source="subscription").exists())
        self.assertTrue(
            PlanAccess.objects.filter(
                user=self.user, plan=self.free_plan, source="purchase"
            ).exists()
        )


class SyncFromStripeTests(TestCase):
    def setUp(self):
        self.cat = PlanCategory.objects.create(
            name="Exercise", slug="exercise")
        self.premium = Plan.objects.create(
            category=self.cat,
            title="Elite",
            description="x",
            price="99.00",
            premium_only=True,
        )
        self.user = User.objects.create_user(
            email="a@example.com", password="pw12345!")
        self.user.stripe_customer_id = "cus_1"
        self.user.save(update_fields=["stripe_customer_id"])

    def test_creates_subscription_and_reads_period_from_item(self):
        sync_from_stripe_subscription(fake_stripe_sub(period_end=1893456000))
        sub = Subscription.objects.get(user=self.user)
        self.assertEqual(sub.status, "active")
        self.assertEqual(
            sub.current_period_end,
            datetime.fromtimestamp(1893456000, tz=dt_timezone.utc),
        )
        self.assertTrue(
            PlanAccess.objects.filter(
                user=self.user,
                plan=self.premium).exists())

    def test_idempotent_on_redelivery(self):
        sync_from_stripe_subscription(fake_stripe_sub())
        sync_from_stripe_subscription(fake_stripe_sub())
        self.assertEqual(
            Subscription.objects.filter(
                user=self.user).count(), 1)

    def test_canceled_revokes_access(self):
        sync_from_stripe_subscription(fake_stripe_sub())
        sync_from_stripe_subscription(fake_stripe_sub(status="canceled"))
        self.assertFalse(
            PlanAccess.objects.filter(
                user=self.user,
                source="subscription").exists())

    def test_unknown_customer_is_ignored(self):
        sync_from_stripe_subscription(
            fake_stripe_sub(
                customer_id="cus_unknown"))
        self.assertEqual(Subscription.objects.count(), 0)


class WebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="a@example.com", password="pw12345!")
        self.user.stripe_customer_id = "cus_1"
        self.user.save(update_fields=["stripe_customer_id"])
        self.cat = PlanCategory.objects.create(
            name="Exercise", slug="exercise")
        Plan.objects.create(
            category=self.cat,
            title="Elite",
            description="x",
            price="99.00",
            premium_only=True,
        )

    @patch("subscriptions.views.stripe.Webhook.construct_event")
    def test_invalid_signature_returns_400(self, construct):
        construct.side_effect = stripe.SignatureVerificationError("bad", "sig")
        resp = self.client.post(
            reverse("subscriptions:webhook"),
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="x",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("subscriptions.views.stripe.Webhook.construct_event")
    def test_subscription_created_upserts(self, construct):
        construct.return_value = {
            "type": "customer.subscription.created",
            "data": {"object": fake_stripe_sub()},
        }
        resp = self.client.post(
            reverse("subscriptions:webhook"),
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="x",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            Subscription.objects.filter(
                user=self.user,
                status="active").exists())


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class PricingSubscribeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="a@example.com", password="pw12345!")

    def test_pricing_page_public(self):
        resp = self.client.get(reverse("subscriptions:pricing"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Premium")

    def test_subscribe_requires_login(self):
        resp = self.client.post(reverse("subscriptions:subscribe"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    @patch("subscriptions.views.stripe.checkout.Session.create")
    @patch("subscriptions.views.stripe.Customer.create")
    def test_subscribe_creates_customer_once_and_redirects(
        self, cust_create, sess_create
    ):
        cust_create.return_value = type("C", (), {"id": "cus_new"})
        sess_create.return_value = type(
            "S", (), {"url": "https://stripe.test/checkout"}
        )
        self.client.force_login(self.user)
        resp = self.client.post(reverse("subscriptions:subscribe"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "https://stripe.test/checkout")
        self.user.refresh_from_db()
        self.assertEqual(self.user.stripe_customer_id, "cus_new")

    @patch("subscriptions.views.stripe.checkout.Session.create")
    @patch("subscriptions.views.stripe.Customer.create")
    def test_subscribe_reuses_existing_customer(
            self, cust_create, sess_create):
        sess_create.return_value = type(
            "S", (), {"url": "https://stripe.test/checkout"}
        )
        self.user.stripe_customer_id = "cus_existing"
        self.user.save(update_fields=["stripe_customer_id"])
        self.client.force_login(self.user)
        self.client.post(reverse("subscriptions:subscribe"))
        cust_create.assert_not_called()
        self.assertEqual(
            sess_create.call_args.kwargs["customer"],
            "cus_existing")


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ManageCancelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="a@example.com", password="pw12345!")
        self.client.force_login(self.user)

    def test_manage_empty_state_without_subscription(self):
        resp = self.client.get(reverse("subscriptions:manage"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Pricing")

    def test_manage_shows_status(self):
        Subscription.objects.create(
            user=self.user,
            stripe_subscription_id="sub_1",
            stripe_customer_id="cus_1",
            status="active",
        )
        resp = self.client.get(reverse("subscriptions:manage"))
        self.assertContains(resp, "active")

    @patch("subscriptions.views.stripe.Subscription.modify")
    def test_cancel_sets_flag_and_calls_stripe(self, modify):
        Subscription.objects.create(
            user=self.user,
            stripe_subscription_id="sub_1",
            stripe_customer_id="cus_1",
            status="active",
        )
        resp = self.client.post(reverse("subscriptions:cancel"))
        self.assertEqual(resp.status_code, 302)
        modify.assert_called_once_with("sub_1", cancel_at_period_end=True)
        self.assertTrue(
            Subscription.objects.get(
                user=self.user).cancel_at_period_end)


@override_settings(STORAGES=SIMPLE_STATIC_STORAGES)
class ContextProcessorTests(TestCase):
    def test_is_premium_true_for_active_subscriber(self):
        user = User.objects.create_user(
            email="a@example.com", password="pw12345!")
        Subscription.objects.create(
            user=user,
            stripe_subscription_id="sub_1",
            stripe_customer_id="cus_1",
            status="active",
        )
        self.client.force_login(user)
        resp = self.client.get(reverse("subscriptions:pricing"))
        self.assertTrue(resp.context["is_premium"])

    def test_is_premium_false_for_anonymous(self):
        resp = self.client.get(reverse("subscriptions:pricing"))
        self.assertFalse(resp.context["is_premium"])
