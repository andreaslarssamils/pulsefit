from django.urls import path

from .views import PlanDetailView, PlanListView

app_name = "plans"

urlpatterns = [
    path("", PlanListView.as_view(), name="list"),
    path("<slug:slug>/", PlanDetailView.as_view(), name="detail"),
]
