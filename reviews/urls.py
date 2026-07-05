from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "add/<str:target_type>/<int:target_id>/",
        views.review_create,
        name="add"),
    path(
        "<int:pk>/delete/",
        views.review_delete,
        name="delete"),
]
