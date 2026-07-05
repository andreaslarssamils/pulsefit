from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path(
        "",
        views.cart_detail,
        name="detail"),
    path(
        "add/<str:item_type>/<int:item_id>/",
        views.add_to_cart,
        name="add"),
    path(
        "update/<str:item_type>/<int:item_id>/",
        views.update_cart,
        name="update"),
    path(
        "remove/<str:item_type>/<int:item_id>/",
        views.remove_from_cart,
        name="remove"),
]
