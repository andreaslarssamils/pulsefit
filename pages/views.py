from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.generic import TemplateView

from dashboard.models import WorkoutLog
from plans.models import Plan
from reviews.models import Review

User = get_user_model()


class HomeView(TemplateView):
    """Marketing landing page served at / (US-39, Sprint 8).

    The hero stats and testimonials are live data, not hard-coded: counts come
    straight off the models and the testimonials are the newest 5★ reviews.
    """

    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["member_count"] = User.objects.filter(is_active=True).count()
        ctx["workout_count"] = WorkoutLog.objects.count()
        ctx["plan_count"] = Plan.objects.count()
        ctx["testimonials"] = (
            Review.objects.filter(rating=5)
            .select_related("user", "plan", "product")
            .order_by("-created_at")[:4]
        )
        return ctx


# Private / transactional prefixes crawlers should skip
ROBOTS_DISALLOW = [
    "/admin/",
    "/accounts/",
    "/dashboard/",
    "/cart/",
    "/orders/",
    "/subscription/",
]


def robots_txt(request):
    """Serve /robots.txt pointing crawlers at the sitemap."""
    lines = ["User-agent: *"]
    lines += [f"Disallow: {path}" for path in ROBOTS_DISALLOW]
    lines += ["", f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
