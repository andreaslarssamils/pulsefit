from orders.models import OrderItem
from plans.access import has_plan_access

# Order statuses that mean the customer has actually paid for the item.
PURCHASED_STATUSES = ("paid", "shipped")


def can_review(user, *, plan=None, product=None) -> bool:
    """
    A user may review a plan they hold ``PlanAccess`` for, or a product they have
    a completed (paid/shipped) order line for. Anonymous users can never review.
    """
    if not user.is_authenticated:
        return False
    if plan is not None:
        return has_plan_access(user, plan)
    if product is not None:
        return OrderItem.objects.filter(
            product=product,
            order__user=user,
            order__status__in=PURCHASED_STATUSES,
        ).exists()
    return False
