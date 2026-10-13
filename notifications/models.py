from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.db import models

from subscriptions.models import Subscription


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications", verbose_name=_("المستخدم")
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("الاشتراك"),
    )
    title = models.CharField(_("العنوان"), max_length=150)
    message = models.TextField(_("الرسالة"))
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    is_read = models.BooleanField(_("مقروء"), default=False)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = _("إشعار")
        verbose_name_plural = _("الإشعارات")

    def __str__(self):
        return self.title


class ReminderLog(models.Model):
    """One row per reminder already issued; the unique constraint prevents repeats."""

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="reminder_logs", verbose_name=_("الاشتراك")
    )
    renewal_date = models.DateField(_("تاريخ التجديد"))
    days_before = models.PositiveSmallIntegerField(_("الأيام قبل التجديد"))
    sent_at = models.DateTimeField(_("وقت الإرسال"), auto_now_add=True)
    channel = models.CharField(_("القناة"), max_length=20, default="in_app")

    class Meta:
        ordering = ["-sent_at", "-id"]
        verbose_name = _("سجل تذكير")
        verbose_name_plural = _("سجلات التذكير")
        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "renewal_date", "days_before"],
                name="uniq_reminder_per_due_date",
                violation_error_message=_("تم إنشاء هذا التذكير مسبقًا."),
            )
        ]

    def __str__(self):
        return f"{self.subscription} - {self.renewal_date} ({self.days_before}d)"
