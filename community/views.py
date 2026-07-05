from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CommunityPostForm
from .models import CommunityPost

User = get_user_model()


def _feed_context(request, form=None):
    if form is None and request.user.is_authenticated:
        form = CommunityPostForm()
    return {
        "posts": CommunityPost.objects.select_related("user"),
        "form": form,
        "stats": {
            "members": User.objects.filter(is_active=True).count(),
            "posts": CommunityPost.objects.count(),
            "new_this_week": CommunityPost.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
        },
    }


def feed(request):
    """Public community feed (US-22)."""
    return render(request, "community/feed.html", _feed_context(request))


@login_required
@require_POST
def post_create(request):
    """Create a post from the feed composer """
    form = CommunityPostForm(request.POST)
    if form.is_valid():
        post = form.save(commit=False)
        post.user = request.user
        post.save()
        messages.success(request, "Post shared with the community.")
        return redirect("community:feed")
    messages.error(request, "Please fix the errors below.")
    return render(
        request,
        "community/feed.html",
        _feed_context(request, form=form)
    )


@login_required
def post_delete(request, pk):
    """Delete one of the user's own posts, with confirmation (US-24)."""
    post = get_object_or_404(CommunityPost, pk=pk, user=request.user)
    if request.method == "POST":
        post.delete()
        messages.success(request, "Post deleted.")
        return redirect("community:feed")
    return render(request,
                  "community/post_confirm_delete.html",
                  {"post": post})
