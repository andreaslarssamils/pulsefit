from django.urls import path

from . import views

app_name = "challenges"

urlpatterns = [
    path("", views.ChallengeListView.as_view(), name="list"),
]
