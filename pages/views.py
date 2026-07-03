from django.http import HttpResponse
from django.views.generic import TemplateView


class ComingSoonView(TemplateView):
    template_name = "pages/coming_soon.html"


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
