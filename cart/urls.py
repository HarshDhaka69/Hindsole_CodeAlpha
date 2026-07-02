from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_view, name="view"),
    path("add/", views.add_to_cart, name="add"),
    path("item/<int:item_id>/update/", views.update_cart_item, name="update_item"),
    path("item/<int:item_id>/remove/", views.remove_cart_item, name="remove_item"),
]
