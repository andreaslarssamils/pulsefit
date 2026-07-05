from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from plans.models import Plan
from products.models import Product

from .access import can_review
from .forms import ReviewForm
from .models import Review


def _resolve_target(target_type, target_id):
    """Return {"plan": obj} or {"product": obj} for the review's
    target, or 404."""
    if target_type == "plan":
        return {"plan": get_object_or_404(Plan, pk=target_id, is_active=True)}
    if target_type == "product":
        return {
            "product": get_object_or_404(
                Product,
                pk=target_id,
                is_active=True)}
    raise Http404("Unknown review target")


@login_required
@require_POST
def review_create(request, target_type, target_id):
    """Create or replace the user's review for a plan or product """
    target = _resolve_target(target_type, target_id)
    obj = target.get("plan") or target.get("product")
    if not can_review(request.user, **target):
        messages.error(
            request,
            "You need access to this item before reviewing it.")
        return redirect(obj.get_absolute_url())
    form = ReviewForm(request.POST)
    if form.is_valid():
        _, created = Review.objects.update_or_create(
            user=request.user,
            **target,
            defaults={
                "rating": form.cleaned_data["rating"],
                "body": form.cleaned_data["body"],
            },
        )
        messages.success(
            request,
            "Review posted." if created else "Review updated.")
    else:
        messages.error(request, "Please fix the errors in your review.")
    return redirect(obj.get_absolute_url())


@login_required
@require_POST
def review_delete(request, pk):
    """Delete one of the user's own reviews"""
    review = get_object_or_404(Review, pk=pk, user=request.user)
    target_url = review.target.get_absolute_url()
    review.delete()
    messages.success(request, "Your review was removed.")
    return redirect(target_url)
