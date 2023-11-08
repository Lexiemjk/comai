from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ("email", "is_staff", "is_active", "first_connection", "answerGenerationPreferences")
    list_filter = ("email", "is_staff", "is_active", "first_connection")
    fieldsets = (
        (None, {"fields": ("username", "email", "password", "first_name", "last_name", "answerGenerationPreferences")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "email", "password1", "password2","first_name", "last_name", "is_staff",
                "is_active","first_connection", "groups", "user_permissions", "answerGenerationPreferences"
            )}
         ),
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)


admin.site.register(CustomUser, CustomUserAdmin)