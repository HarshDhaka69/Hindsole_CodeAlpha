from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("shop/", views.ProductListView.as_view(), name="list"),
    path("shop/grid/", views.ProductGridPartialView.as_view(), name="list_grid_partial"),
    path("product/<slug:slug>/", views.ProductDetailView.as_view(), name="detail"),
    path(
        "product/<slug:slug>/gallery/",
        views.product_gallery_partial,
        name="gallery_partial",
    ),
    path("toggle-dark-mode/", views.toggle_dark_mode, name="toggle_dark_mode"),
]
