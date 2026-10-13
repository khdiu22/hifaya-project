from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "account_type", "business_name", "created_at")
    list_filter = ("account_type",)
    search_fields = ("user__username", "user__email", "business_name")
