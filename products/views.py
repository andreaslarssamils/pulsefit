from django.views.generic import DetailView, ListView

from reviews.context import review_context

from .models import Product, ProductCategory


class ProductListView(ListView):
    """Public shop listing of active products (US-07). Category filtering is client-side."""

    template_name = "products/product_list.html"
    context_object_name = "products"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = ProductCategory.objects.all()
        return context


class ProductDetailView(DetailView):
    """Slug-based product detail page (US-08). Inactive products 404."""

    template_name = "products/product_detail.html"
    context_object_name = "product"
    queryset = Product.objects.filter(is_active=True).select_related("category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(review_context(self.request.user, product=self.object))
        return context
