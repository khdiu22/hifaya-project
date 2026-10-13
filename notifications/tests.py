from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.testing import make_subscription, make_user

from .models import Notification, ReminderLog
from .services import reminder_text, send_due_reminders

TODAY = timezone.localdate()


class ReminderLogicTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def due_sub(self, days=3, remind=3, **kw):
        return make_subscription(self.user, next_renewal_date=TODAY + timedelta(days=days), reminder_days_before=remind, **kw)

    def test_reminder_created_with_emoji_and_email(self):
        sub = self.due_sub()
        result = send_due_reminders()
        self.assertEqual(result.created, 1)
        note = Notification.objects.get()
        self.assertEqual((note.user, note.subscription, note.is_read), (self.user, sub, False))
        self.assertIn("⏳", note.message)
        self.assertIn("3 أيام", note.message)
        self.assertEqual(ReminderLog.objects.get().channel, "in_app+email")
        self.assertEqual(len(mail.outbox), 1)

    def test_no_duplicate_for_same_due_date(self):
        self.due_sub()
        send_due_reminders()
        second = send_due_reminders()
        self.assertEqual(second.created, 0)
        self.assertEqual(second.skipped_duplicates, 1)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(ReminderLog.objects.count(), 1)

    def test_not_due_yet_or_already_past(self):
        self.due_sub(days=5, remind=3, service_name="Later")
        self.due_sub(days=-1, remind=3, service_name="Past", start_date=TODAY - timedelta(days=60))
        self.assertEqual(send_due_reminders().created, 0)

    def test_inactive_subscriptions_get_no_reminders(self):
        for status in ("paused", "cancelled", "archived"):
            self.due_sub(status=status, service_name=status)
        self.assertEqual(send_due_reminders().created, 0)
        self.assertFalse(Notification.objects.exists())

    def test_new_renewal_date_allows_new_reminder(self):
        sub = self.due_sub()
        send_due_reminders()
        sub.next_renewal_date = TODAY + timedelta(days=2)
        sub.save()
        self.assertEqual(send_due_reminders().created, 1)
        self.assertEqual(ReminderLog.objects.count(), 2)

    def test_user_scope(self):
        self.due_sub()
        other = make_user("other@example.com")
        self.assertEqual(send_due_reminders(user=other).created, 0)
        self.assertEqual(send_due_reminders(user=self.user).created, 1)

    def test_database_rejects_duplicate_log(self):
        sub = self.due_sub()
        ReminderLog.objects.create(subscription=sub, renewal_date=sub.next_renewal_date, days_before=3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ReminderLog.objects.create(subscription=sub, renewal_date=sub.next_renewal_date, days_before=3)

    def test_message_wording(self):
        self.assertIn("اليوم", reminder_text("X", 0))
        self.assertIn("يوم واحد", reminder_text("X", 1))
        self.assertIn("يومان", reminder_text("X", 2))
        self.assertIn("5 أيام", reminder_text("X", 5))

    def test_management_command(self):
        self.due_sub()
        out = StringIO()
        call_command("send_reminders", stdout=out)
        self.assertIn("Reminders created: 1", out.getvalue())

    def test_management_command_today_option(self):
        make_subscription(self.user, next_renewal_date=TODAY + timedelta(days=30))
        out = StringIO()
        call_command("send_reminders", today=(TODAY + timedelta(days=28)).isoformat(), stdout=out)
        self.assertIn("Reminders created: 1", out.getvalue())
        with self.assertRaises(CommandError):
            call_command("send_reminders", today="not-a-date")


class NotificationViewTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def make(self, user=None, **kw):
        data = {"user": user or self.user, "title": "t", "message": "m"}
        data.update(kw)
        return Notification.objects.create(**data)

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("notifications:list")).status_code, 302)

    def test_empty_state(self):
        self.assertContains(self.client.get(reverse("notifications:list")), "لا توجد إشعارات حاليًا")

    def test_only_own_and_newest_first(self):
        old = self.make(title="old")
        new = self.make(title="new")
        Notification.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=3))
        self.make(user=make_user("other@example.com"), title="theirs")
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual([n.pk for n in response.context["page_obj"]], [new.pk, old.pk])

    def test_filter_by_read_state_and_date(self):
        unread = self.make(title="u")
        read = self.make(title="r", is_read=True)
        ids = lambda **p: [n.pk for n in self.client.get(reverse("notifications:list"), p).context["page_obj"]]
        self.assertEqual(ids(state="unread"), [unread.pk])
        self.assertEqual(ids(state="read"), [read.pk])
        self.assertEqual(len(ids(date_from=TODAY.isoformat())), 2)
        self.assertEqual(ids(date_to=(TODAY - timedelta(days=5)).isoformat()), [])

    def test_mark_read_and_mark_all(self):
        a, b = self.make(), self.make()
        self.client.post(reverse("notifications:read", args=[a.pk]))
        a.refresh_from_db()
        self.assertTrue(a.is_read)
        self.client.post(reverse("notifications:read_all"))
        b.refresh_from_db()
        self.assertTrue(b.is_read)

    def test_cannot_mark_other_users_notification(self):
        theirs = self.make(user=make_user("other@example.com"))
        self.assertEqual(self.client.post(reverse("notifications:read", args=[theirs.pk])).status_code, 404)
        theirs.refresh_from_db()
        self.assertFalse(theirs.is_read)

    def test_mark_read_ignores_external_redirect(self):
        note = self.make()
        response = self.client.post(reverse("notifications:read", args=[note.pk]), {"next": "https://evil.example/"})
        self.assertEqual(response["Location"], reverse("notifications:list"))

    def test_check_button_creates_only_own_reminders(self):
        make_subscription(self.user, next_renewal_date=TODAY + timedelta(days=2))
        other = make_user("other@example.com")
        make_subscription(other, next_renewal_date=TODAY + timedelta(days=2))
        self.client.post(reverse("notifications:check"))
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Notification.objects.filter(user=other).count(), 0)

    def test_unread_count_in_sidebar_context(self):
        self.make()
        self.make(is_read=True)
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.context["unread_count"], 1)


class ReminderLanguageTests(TestCase):
    """Reminders (in-app + e-mail) are written in each user's saved language, even when a scheduler runs them."""

    def setUp(self):
        self.arabic_user = make_user("ar@example.com")
        self.english_user = make_user("en@example.com")
        self.english_user.profile.preferred_language = "en"
        self.english_user.profile.save()
        for user in (self.arabic_user, self.english_user):
            make_subscription(user, next_renewal_date=TODAY + timedelta(days=3), reminder_days_before=3)

    def test_each_user_gets_the_language_saved_in_the_account(self):
        send_due_reminders()
        arabic = Notification.objects.get(user=self.arabic_user)
        english = Notification.objects.get(user=self.english_user)
        self.assertEqual(arabic.title, "🔔 تذكير بتجديد Netflix")
        self.assertIn("3 أيام", arabic.message)
        self.assertEqual(english.title, "🔔 Renewal reminder for Netflix")
        self.assertIn("renews in 3 days", english.message)

    def test_email_text_follows_the_saved_language(self):
        send_due_reminders()
        mails = {m.to[0]: m for m in mail.outbox}
        self.assertEqual(mails["ar@example.com"].subject, "تذكير بتجديد Netflix")
        self.assertEqual(mails["en@example.com"].subject, "Renewal reminder for Netflix")
        self.assertIn("renews in 3 days", mails["en@example.com"].body)
        self.assertIn("3 أيام", mails["ar@example.com"].body)

    def test_scheduler_command_uses_saved_languages_and_never_sends_twice(self):
        call_command("send_reminders", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 2)
        call_command("send_reminders", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(ReminderLog.objects.count(), 2)

    def test_check_button_creates_reminders_in_the_users_language(self):
        self.client.force_login(self.english_user)
        self.client.post(reverse("notifications:check"))
        self.assertEqual(Notification.objects.get(user=self.english_user).title, "🔔 Renewal reminder for Netflix")
