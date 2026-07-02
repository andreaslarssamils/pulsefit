from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("post/", views.post_create, name="post_create"),
    path("post/<int:pk>/delete/", views.post_delete, name="post_delete"),
]
