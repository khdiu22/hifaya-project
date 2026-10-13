from django.contrib import admin

from .models import Category, Subscription


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("service_name", "user", "category", "amount", "currency", "billing_cycle", "next_renewal_date", "status")
    list_filter = ("status", "billing_cycle", "currency", "category")
    search_fields = ("service_name", "user__username", "user__email")
