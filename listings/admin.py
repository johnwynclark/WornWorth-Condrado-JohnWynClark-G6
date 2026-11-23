from django.contrib import admin

from .models import Category, Listing, ListingImage


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("category_name", "description")
    search_fields = ("category_name",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "category", "price", "quantity", "listing_status", "created_at")
    list_filter = ("listing_status", "category", "condition")
    search_fields = ("title", "seller__email")
    inlines = [ListingImageInline]
