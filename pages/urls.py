from django.urls import path

from .views import ComingSoonView

app_name = "core"

urlpatterns = [
    path("", ComingSoonView.as_view(), name="coming_soon"),
]
