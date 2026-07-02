from .models import Subscription


def subscription_status(request):
    is_premium = False
    if request.user.is_authenticated:
        sub = Subscription.objects.filter(user=request.user).first()
        is_premium = bool(sub and sub.is_active)
    return {"is_premium": is_premium}
