from django.contrib import admin

from .models import Notification, ReminderLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "subscription", "is_read", "created_at")
    list_filter = ("is_read",)


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = ("subscription", "renewal_date", "days_before", "channel", "sent_at")
