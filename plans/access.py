from .models import PlanAccess


def has_plan_access(user, plan) -> bool:
    """True if the user holds any PlanAccess row for this plan """
    return (
        user.is_authenticated
        and PlanAccess.objects.filter(user=user, plan=plan).exists()
    )
