from django.contrib import messages
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import NewsletterForm
from .services import AlreadySubscribed, NewsletterError, subscribe_email


def _redirect_back(request, default="/"):
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
            referer,
            allowed_hosts={
                request.get_host()},
            require_https=request.is_secure()):
        return redirect(referer)
    return redirect(default)


@require_POST
def subscribe(request):
    form = NewsletterForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please enter a valid email address.")
        return _redirect_back(request)

    try:
        subscribe_email(form.cleaned_data["email"])
    except AlreadySubscribed:
        messages.info(
            request,
            "You're already subscribed — thanks for being with us!")
    except NewsletterError:
        messages.error(
            request,
            "Something went wrong. Please try again later.")
    else:
        messages.success(
            request, "You're subscribed! Check your inbox for fitness tips."
        )
    return _redirect_back(request)
