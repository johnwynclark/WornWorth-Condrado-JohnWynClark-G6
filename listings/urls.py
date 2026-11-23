from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("browse/", views.browse, name="browse"),
    path("listings/<int:pk>/", views.listing_detail, name="detail"),
    # seller
    path("seller/listings/", views.my_listings, name="my_listings"),
    path("seller/listings/new/", views.listing_create, name="create"),
    path("seller/listings/<int:pk>/edit/", views.listing_edit, name="edit"),
    path("seller/listings/<int:pk>/status/", views.listing_status, name="status"),
    path("seller/listings/<int:pk>/delete/", views.listing_delete, name="delete"),
    path("seller/listings/<int:pk>/images/add/", views.image_add, name="image_add"),
    path("seller/images/<int:image_pk>/delete/", views.image_delete, name="image_delete"),
    path("seller/images/<int:image_pk>/primary/", views.image_primary, name="image_primary"),
    # admin moderation
    path("manage/listings/", views.admin_listings, name="admin_list"),
    path("manage/listings/<int:pk>/remove/", views.admin_remove, name="admin_remove"),
    path("manage/listings/<int:pk>/restore/", views.admin_restore, name="admin_restore"),
]
