import stripe
from django.conf import settings
from django.core.management.base import BaseCommand

from subscriptions.services import sync_from_stripe_subscription

stripe.api_key = settings.STRIPE_SECRET_KEY


class Command(BaseCommand):
    help = (
        "Backfill/reconcile local Subscription rows and premium access "
        "from Stripe. Run once to repair subscriptions that were paid "
        "for but never activated (e.g. while the webhook was "
        "misconfigured), and safely re-runnable thereafter."
    )

    def handle(self, *args, **options):
        synced = 0
        failed = 0
        subscriptions = stripe.Subscription.list(status="all", limit=100)
        for stripe_sub in subscriptions.auto_paging_iter():
            try:
                sync_from_stripe_subscription(stripe_sub)
                synced += 1
            except Exception as exc:  # noqa: BLE001 - report and continue
                failed += 1
                self.stderr.write(
                    f"Failed to sync {stripe_sub['id']}: {exc}"
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {synced} subscription(s), {failed} failure(s)."
            )
        )
