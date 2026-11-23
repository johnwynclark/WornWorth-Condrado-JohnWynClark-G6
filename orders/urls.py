from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/<int:listing_pk>/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="list"),
    path("orders/<int:pk>/", views.order_detail, name="detail"),
    path("orders/<int:pk>/cancel/", views.order_cancel, name="cancel"),
    path("orders/<int:pk>/advance/", views.order_advance, name="advance"),
    path("orders/<int:pk>/received/", views.order_received, name="received"),
]
