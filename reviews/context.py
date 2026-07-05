from django.db.models import Avg, Count

from .access import can_review
from .forms import ReviewForm


def review_context(user, *, plan=None, product=None):
    """Shared context for the reviews section on a plan/product page.

    Supplies the average rating, count, the visitor's own review
    (if any), a prefilled form, and the write gate. Used by both
    PlanDetailView and ProductDetailView.
    """
    target = plan if plan is not None else product
    reviews = target.reviews.select_related("user")
    agg = reviews.aggregate(avg=Avg("rating"), count=Count("id"))
    user_review = reviews.filter(
        user=user).first() if user.is_authenticated else None
    gate = {"plan": plan} if plan is not None else {"product": product}
    return {
        "reviews": reviews,
        "avg_rating": agg["avg"],
        "review_count": agg["count"],
        "user_review": user_review,
        "review_form": ReviewForm(instance=user_review),
        "can_review": can_review(user, **gate),
        "review_target_type": "plan" if plan is not None else "product",
        "review_target_id": target.id,
    }
