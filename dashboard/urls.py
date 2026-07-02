from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("log/", views.log_workout, name="log_workout"),
    path("goal/", views.set_goal, name="set_goal"),
]
