"""Create FICTIONAL demo data: python manage.py seed_demo [--reset]

Accounts created (password printed once, or taken from DEMO_PASSWORD):
  demo.individual@example.com  - individual account with rich data
  demo.business@example.com    - business account ("شركة النخبة التجريبية")
  demo.empty@example.com       - account with no data (to show empty states)
"""
import os
import secrets
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Profile
from notifications.models import Notification
from notifications.services import send_due_reminders
from payments.models import Payment
from payments.services import flag_similar
from subscriptions.models import Category, Subscription

User = get_user_model()
INDIVIDUAL, BUSINESS, EMPTY = (
    "demo.individual@example.com",
    "demo.business@example.com",
    "demo.empty@example.com",
)
S = Subscription


class Command(BaseCommand):
    help = "Load fictional demo accounts, subscriptions, payments and notifications."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing demo accounts first.")

    @transaction.atomic
    def handle(self, *args, **options):
        emails = [INDIVIDUAL, BUSINESS, EMPTY]
        existing = User.objects.filter(username__in=emails)
        if existing.exists():
            if not options["reset"]:
                raise CommandError("Demo accounts already exist. Re-run with --reset to recreate them.")
            existing.delete()  # cascades to their subscriptions, payments and notifications

        password = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(9)
        today = timezone.localdate()
        cat = {c.name: c for c in Category.objects.all()}
        if not cat:
            raise CommandError("No categories found. Run `python manage.py migrate` first.")

        def make_user(email, name, account_type, business=""):
            user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
            Profile.objects.create(user=user, account_type=account_type, business_name=business)
            return user

        ind = make_user(INDIVIDUAL, "سارة (تجريبي)", Profile.AccountType.INDIVIDUAL)
        biz = make_user(BUSINESS, "مدير المنشأة (تجريبي)", Profile.AccountType.BUSINESS, "شركة النخبة التجريبية")
        make_user(EMPTY, "حساب فارغ (تجريبي)", Profile.AccountType.INDIVIDUAL)

        def sub(user, name, category, amount, currency, cycle, start_ago, renew_in, status=S.Status.ACTIVE,
                recurring=True, remind=3, notes=""):
            return Subscription.objects.create(
                user=user, category=cat[category], service_name=name, amount=Decimal(amount), currency=currency,
                billing_cycle=cycle, start_date=today - timedelta(days=start_ago),
                next_renewal_date=today + timedelta(days=renew_in), status=status,
                is_recurring=recurring, reminder_days_before=remind, notes=notes,
            )

        def pay(user, subscription, amount, currency, days_ago, status=Payment.Status.PAID, method="بطاقة", ref="", notes=""):
            payment = Payment.objects.create(
                user=user, subscription=subscription, amount=Decimal(amount), currency=currency,
                payment_date=today - timedelta(days=days_ago), status=status, payment_method=method,
                reference=ref, notes=notes,
            )
            flag_similar(payment)
            return payment

        ENT, AI, STO, DES, SHOP, GAME, EDU, OTHER = (
            "الترفيه والموسيقى", "الذكاء الاصطناعي", "التخزين والإنتاجية", "التصميم والأدوات",
            "التسوق والخدمات الرقمية", "الألعاب", "التعليم", "أخرى",
        )
        M, W, Q, Y = S.BillingCycle.MONTHLY, S.BillingCycle.WEEKLY, S.BillingCycle.QUARTERLY, S.BillingCycle.YEARLY

        # ---------- individual ----------
        netflix = sub(ind, "Netflix", ENT, "45.00", "SAR", M, 200, 3, notes="الباقة العائلية")
        spotify = sub(ind, "Spotify", ENT, "22.00", "SAR", M, 150, 12)
        chatgpt = sub(ind, "ChatGPT", AI, "20.00", "USD", M, 90, 1, remind=2)
        icloud = sub(ind, "iCloud", STO, "3.99", "USD", M, 300, 20)
        canva = sub(ind, "Canva", DES, "150.00", "SAR", Q, 120, 40)
        sub(ind, "Adobe Creative Cloud", DES, "250.00", "SAR", M, 400, 9, status=S.Status.PAUSED)
        dropbox = sub(ind, "Dropbox", STO, "119.99", "USD", Y, 700, 60, status=S.Status.CANCELLED, recurring=False)
        sub(ind, "Duolingo Super", EDU, "40.00", "EUR", Y, 50, 120)
        sub(ind, "Notion", STO, "8.00", "USD", M, 260, -5, notes="تاريخ التجديد مضى: يحتاج مراجعة")
        sub(ind, "Zoom", STO, "15.00", "SAR", W, 30, 5)
        sub(ind, "Amazon Prime", SHOP, "599.00", "SAR", Y, 100, 60, recurring=False)
        sub(ind, "نادي القراءة الرقمي", OTHER, "30.00", "SAR", M, 60, 15, notes="خدمة مخصّصة تظهر بأيقونة الكوكب")
        sub(ind, "Anghami", ENT, "20.00", "SAR", M, 500, 25, status=S.Status.ARCHIVED)

        pay(ind, netflix, "45.00", "SAR", 62, ref="NF-001")
        pay(ind, netflix, "45.00", "SAR", 32, ref="NF-002")
        pay(ind, netflix, "45.00", "SAR", 2, ref="NF-003")
        pay(ind, netflix, "45.00", "SAR", 1, ref="NF-003B", notes="مدفوعة مرتين تقريبًا في يومين: مثال للمراجعة")
        pay(ind, spotify, "22.00", "SAR", 40, method="Apple Pay")
        pay(ind, spotify, "22.00", "SAR", 10, method="Apple Pay")
        pay(ind, chatgpt, "20.00", "USD", 30, method="Visa")
        pay(ind, chatgpt, "20.00", "USD", 0, method="Visa")
        pay(ind, canva, "150.00", "SAR", 80, method="مدى")
        pay(ind, icloud, "3.99", "USD", 12, method="Apple Pay")
        pay(ind, dropbox, "119.99", "USD", 320, method="Visa", notes="آخر دفعة قبل الإلغاء")
        pay(ind, None, "100.00", "SAR", 15, method="تحويل", ref="MISC-1", notes="دفعة بدون اشتراك محدد")
        pay(ind, spotify, "22.00", "SAR", 5, status=Payment.Status.FAILED, method="مدى", notes="فشلت العملية")

        # ---------- business ----------
        ms = sub(biz, "Microsoft 365", STO, "500.00", "SAR", M, 365, 4, remind=5)
        gw = sub(biz, "Google Workspace", STO, "360.00", "SAR", M, 300, 18)
        zoom = sub(biz, "Zoom", STO, "60.00", "USD", M, 200, 2, remind=3)
        gh = sub(biz, "GitHub", DES, "4.00", "USD", M, 250, 28)
        figma = sub(biz, "Figma", DES, "15.00", "USD", M, 180, -2, notes="تجديد متأخر: يحتاج مراجعة")
        sub(biz, "JetBrains", DES, "649.00", "USD", Y, 90, 275)
        sub(biz, "Shahid", ENT, "35.00", "SAR", M, 40, 7, status=S.Status.PAUSED)
        pay(biz, ms, "500.00", "SAR", 60)
        pay(biz, ms, "500.00", "SAR", 30)
        pay(biz, gw, "360.00", "SAR", 25)
        pay(biz, zoom, "60.00", "USD", 28)
        pay(biz, gh, "4.00", "USD", 2)
        pay(biz, figma, "15.00", "USD", 33)

        # ---------- notifications ----------
        reminders = send_due_reminders(today=today)  # real reminders from real dates
        first = Notification.objects.filter(user=ind).first()
        if first:
            Notification.objects.filter(pk=first.pk).update(is_read=True)
        Notification.objects.create(user=ind, title="🎉 أهلًا بك في حفاية", message="ابدأ بإضافة اشتراكاتك ومتابعة تجديداتها. 🔔", is_read=True)
        Notification.objects.create(user=ind, title="💡 نصيحة", message="تقدر تغيّر موعد التذكير من صفحة تعديل أي اشتراك.")

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(f"Reminders created from demo dates: {reminders.created}")
        self.stdout.write("Accounts (all use the same password):")
        for email in emails:
            self.stdout.write(f"  - {email}")
        self.stdout.write(self.style.WARNING(f"Password: {password}"))
