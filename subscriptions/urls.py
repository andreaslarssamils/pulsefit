from django.urls import path

from . import views

app_name = "subscriptions"

urlpatterns = [
    path("subscription/webhook/", views.stripe_webhook, name="webhook"),
    path("pricing/", views.pricing, name="pricing"),
    path("subscription/subscribe/", views.subscribe, name="subscribe"),
    path("subscription/", views.manage, name="manage"),
    path("subscription/cancel/", views.cancel, name="cancel"),
]
