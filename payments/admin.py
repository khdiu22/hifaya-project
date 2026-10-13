from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subscription", "amount", "currency", "payment_date", "status", "review_required", "is_archived")
    list_filter = ("status", "currency", "review_required", "is_archived")
    search_fields = ("reference", "user__username", "subscription__service_name")
