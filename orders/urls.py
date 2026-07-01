from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout_view, name="checkout"),
    path("webhook/", views.stripe_webhook, name="webhook"),
    path("success/", views.order_success_view, name="success"),
    path("cancel/", views.order_cancel_view, name="cancel"),
]
