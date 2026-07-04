from django.views.generic import ListView

from .models import Challenge


class ChallengeListView(ListView):
    """Public, read-only list of active challenges """

    template_name = "challenges/challenge_list.html"
    context_object_name = "challenges"
    queryset = Challenge.objects.filter(is_active=True)
