import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.translation import override

from subscriptions.models import Subscription

from .models import Notification, ReminderLog

logger = logging.getLogger(__name__)
MAX_REMINDER_DAYS = 60  # matches the validator on Subscription.reminder_days_before


def user_language(user):
    """The language saved in the user's profile, so reminders are written in it even when a scheduler runs them."""
    profile = getattr(user, "profile", None)
    language = getattr(profile, "preferred_language", None)
    return language if language in dict(settings.LANGUAGES) else settings.LANGUAGE_CODE


@dataclass
class ReminderResult:
    created: int = 0
    skipped_duplicates: int = 0
    emails_sent: int = 0


def reminder_text(service_name, days_left):
    """Friendly Arabic messages with emojis."""
    if days_left <= 0:
        return _("⏰ اشتراكك في «%(service_name)s» يتجدد اليوم! راجعه الآن 🔔") % {"service_name": service_name}
    if days_left == 1:
        return _("⏳ باقي يوم واحد على تجديد اشتراكك في «%(service_name)s»، سارع بالتعديل! 🔔") % {"service_name": service_name}
    if days_left == 2:
        return _("⏳ باقي يومان على تجديد اشتراكك في «%(service_name)s»، سارع بالتعديل! 🔔") % {"service_name": service_name}
    return _("⏳ باقي على اشتراكك في «%(service_name)s» %(days_left)s أيام ويتجدد، سارع بالتعديل! 🔔") % {"service_name": service_name, "days_left": days_left}


def send_due_reminders(user=None, today=None):
    """Create in-app reminders (and email when configured) for ACTIVE subscriptions
    whose renewal date is within `reminder_days_before` days.

    - inactive (paused / cancelled / archived) subscriptions never get reminders;
    - ReminderLog + its unique constraint stop the same reminder being created twice.
    """
    today = today or timezone.localdate()
    result = ReminderResult()
    candidates = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
        next_renewal_date__gte=today,
        next_renewal_date__lte=today + timedelta(days=MAX_REMINDER_DAYS),
    ).select_related("user", "user__profile")
    if user is not None:
        candidates = candidates.filter(user=user)

    for sub in candidates.order_by("next_renewal_date", "pk"):
        days_left = (sub.next_renewal_date - today).days
        if days_left > sub.reminder_days_before:
            continue
        language = user_language(sub.user)
        with override(language):
            body = reminder_text(sub.service_name, days_left)
            title = _("🔔 تذكير بتجديد %(service_name)s") % {"service_name": sub.service_name}
            subject = _("تذكير بتجديد %(service_name)s") % {"service_name": sub.service_name}
        with transaction.atomic():
            log, is_new = ReminderLog.objects.get_or_create(
                subscription=sub, renewal_date=sub.next_renewal_date, days_before=sub.reminder_days_before
            )
            if not is_new:
                result.skipped_duplicates += 1
                continue
            Notification.objects.create(user=sub.user, subscription=sub, title=title, message=body)
        result.created += 1
        if sub.user.email:
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[sub.user.email],
                    fail_silently=False,
                )
            except Exception:  # noqa: BLE001 - email problems must not break reminders
                logger.warning("Could not email reminder for subscription %s", sub.pk, exc_info=True)
            else:
                ReminderLog.objects.filter(pk=log.pk).update(channel="in_app+email")
                result.emails_sent += 1
    return result
