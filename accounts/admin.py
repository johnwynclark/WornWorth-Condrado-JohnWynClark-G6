from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import AdminChangeForm, AdminCreationForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = AdminChangeForm
    add_form = AdminCreationForm
    ordering = ("-created_at",)
    list_display = ("email", "full_name", "role", "account_status", "created_at")
    list_filter = ("role", "account_status")
    search_fields = ("email", "full_name")
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "phone", "profile_photo")}),
        ("Access", {"fields": ("role", "account_status", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "role", "password1", "password2")}),)
