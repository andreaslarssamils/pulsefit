import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class NewsletterError(Exception):
    """Signup failed: missing config, network error, or a Mailchimp error."""


class AlreadySubscribed(Exception):
    """The email address is already a member of the audience."""


def subscribe_email(email):
    """Add `email` to the configured Mailchimp audience
    """
    api_key = settings.MAILCHIMP_API_KEY
    audience_id = settings.MAILCHIMP_AUDIENCE_ID
    server_prefix = settings.MAILCHIMP_SERVER_PREFIX
    if not (api_key and audience_id and server_prefix):
        raise NewsletterError("Mailchimp is not configured.")

    url = (
        f"https://{server_prefix}.api.mailchimp.com/3.0/lists/"
        f"{audience_id}/members"
    )
    try:
        response = requests.post(
            url,
            auth=("anystring", api_key),
            json={"email_address": email, "status": "subscribed"},
            timeout=5,
        )
    except requests.RequestException as exc:
        logger.warning("Mailchimp request failed: %s", exc)
        raise NewsletterError(str(exc)) from exc

    if response.status_code in (200, 201):
        return None
    if response.status_code == 400:
        try:
            title = response.json().get("title")
        except ValueError:
            title = None
        if title == "Member Exists":
            raise AlreadySubscribed(email)
    logger.warning(
        "Mailchimp error %s: %s",
        response.status_code,
        response.text)
    raise NewsletterError(f"Mailchimp returned {response.status_code}")
