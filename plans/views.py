from django.views.generic import DetailView, ListView

from .models import Plan, PlanCategory


class PlanListView(ListView):
    """Public catalog of active plans (US-05). Category filtering is client-side."""

    template_name = "plans/plan_list.html"
    context_object_name = "plans"

    def get_queryset(self):
        return Plan.objects.filter(is_active=True).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = PlanCategory.objects.all()
        return context


class PlanDetailView(DetailView):
    """Slug-based plan detail page (US-06). Inactive plans 404."""

    template_name = "plans/plan_detail.html"
    context_object_name = "plan"
    queryset = Plan.objects.filter(is_active=True).select_related("category")
