from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/shipping/", views.checkout_shipping, name="checkout_shipping"),
    path("checkout/review/", views.checkout_review, name="checkout_review"),
    path("confirmation/<int:pk>/", views.order_confirmation, name="confirmation"),
    path("history/", views.order_history, name="history"),
    path("<int:pk>/", views.order_detail, name="detail"),
]
