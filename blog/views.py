from django.views.generic import DetailView, ListView

from .models import BlogPost


class BlogListView(ListView):
    """Public list of published posts, newest first (US-25)."""

    template_name = "blog/blog_list.html"
    context_object_name = "posts"
    queryset = BlogPost.objects.filter(status="published")


class BlogDetailView(DetailView):
    """Slug-based post detail (US-26). Drafts return 404."""

    template_name = "blog/blog_detail.html"
    context_object_name = "post"
    queryset = BlogPost.objects.filter(status="published")
