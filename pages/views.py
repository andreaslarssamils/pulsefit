from django.views.generic import TemplateView


class ComingSoonView(TemplateView):
    template_name = "pages/coming_soon.html"
