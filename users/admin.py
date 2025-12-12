from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    fieldsets = list(UserAdmin.fieldsets or []) + [
        ("Extra", {"fields": ("role",)}),
    ]
    list_display = ["username", "email", "first_name", "last_name", "role", "is_staff"]
