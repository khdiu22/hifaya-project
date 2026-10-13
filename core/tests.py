from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .testing import make_payment, make_subscription, make_user
from .theme import THEME_COOKIE

TODAY = timezone.localdate()


class ThemeTests(TestCase):
    """Light/dark mode saved in session + cookie, without JavaScript."""

    def test_default_theme_is_light_and_page_is_rtl_arabic(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, 'data-theme="light"')
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, 'lang="ar"')

    def test_dark_theme_saved_in_session_and_cookie(self):
        response = self.client.post(reverse("core:set_theme"), {"theme": "dark", "next": "/accounts/login/"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["theme"], "dark")
        self.assertEqual(response.cookies[THEME_COOKIE].value, "dark")
        self.assertContains(self.client.get(reverse("accounts:login")), 'data-theme="dark"')

    def test_theme_persists_from_cookie_without_session(self):
        client = self.client_class()
        client.cookies[THEME_COOKIE] = "dark"
        self.assertContains(client.get(reverse("accounts:login")), 'data-theme="dark"')

    def test_invalid_theme_falls_back_to_light(self):
        self.client.post(reverse("core:set_theme"), {"theme": "<script>", "next": "/"})
        self.assertEqual(self.client.session["theme"], "light")

    def test_external_redirect_blocked(self):
        response = self.client.post(reverse("core:set_theme"), {"theme": "dark", "next": "https://evil.example/"})
        self.assertEqual(response["Location"], "/")

    def test_theme_requires_post(self):
        self.assertEqual(self.client.get(reverse("core:set_theme")).status_code, 405)

    def test_logged_in_pages_also_have_theme_toggle(self):
        self.client.force_login(make_user())
        self.assertContains(self.client.get(reverse("core:dashboard")), reverse("core:set_theme"))


class DashboardTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_empty_state_for_new_user(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertContains(response, "لم تضف أي اشتراك بعد")
        self.assertContains(response, reverse("subscriptions:create"))

    def test_statistics_come_from_the_database(self):
        make_subscription(self.user, service_name="Soon", amount=Decimal("10"), next_renewal_date=TODAY + timedelta(days=3))
        make_subscription(self.user, service_name="Later", amount=Decimal("10"), next_renewal_date=TODAY + timedelta(days=20))
        make_subscription(self.user, service_name="Paused", amount=Decimal("10"), status="paused")
        make_subscription(self.user, service_name="Overdue", amount=Decimal("10"), next_renewal_date=TODAY - timedelta(days=2), start_date=TODAY - timedelta(days=60))
        stats = self.client.get(reverse("core:dashboard")).context["stats"]
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["active"], 3)
        self.assertEqual(stats["renewing_soon"], 1)
        self.assertEqual(stats["needs_review"], 1)

    def test_monthly_estimate_uses_active_subscriptions_only(self):
        make_subscription(self.user, service_name="A", amount=Decimal("10"))
        make_subscription(self.user, service_name="B", amount=Decimal("20"))
        make_subscription(self.user, service_name="C", amount=Decimal("500"), status="cancelled")
        make_subscription(self.user, service_name="D", amount=Decimal("5"), currency="USD")
        estimates = {m["currency"]: m["amount"] for m in self.client.get(reverse("core:dashboard")).context["monthly_estimates"]}
        self.assertEqual(estimates, {"SAR": Decimal("30.00"), "USD": Decimal("5.00")})

    def test_latest_payments_limited_and_private(self):
        sub = make_subscription(self.user)
        for i in range(7):
            make_payment(self.user, sub, amount=Decimal(10 + i), payment_date=TODAY - timedelta(days=i * 10))
        other = make_user("other@example.com")
        make_payment(other, make_subscription(other), amount=Decimal("9999"))
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(len(response.context["latest_payments"]), 5)
        self.assertNotContains(response, "9999")

    def test_other_users_subscriptions_not_counted(self):
        other = make_user("other@example.com")
        make_subscription(other)
        self.assertEqual(self.client.get(reverse("core:dashboard")).context["stats"]["total"], 0)

    def test_navigation_has_exactly_five_sections(self):
        make_subscription(self.user)
        response = self.client.get(reverse("core:dashboard"))
        for name in ("لوحة التحكم", "اشتراكاتي", "المدفوعات", "الإشعارات", "التقارير"):
            self.assertContains(response, name)
        self.assertContains(response, 'class="ico"', count=5)


class ErrorPageTests(TestCase):
    def test_unknown_url_shows_friendly_404(self):
        response = self.client.get("/this/does/not/exist/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "الصفحة غير موجودة", status_code=404)


class MigrationsTests(TestCase):
    def test_models_and_migrations_are_in_sync(self):
        try:
            call_command("makemigrations", check=True, dry_run=True, verbosity=0, interactive=False)
        except SystemExit:
            self.fail("Models differ from the migrations. Run `python manage.py makemigrations` and commit the result.")


class LanguageTests(TestCase):
    """Arabic (default) and English, switched with Django's set_language view (no JavaScript)."""

    def test_default_language_is_arabic_rtl(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, 'lang="ar"')
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, "تسجيل الدخول")

    def test_switch_to_english_changes_text_and_direction(self):
        response = self.client.post(reverse("set_language"), {"language": "en", "next": "/accounts/login/"})
        self.assertEqual(response.status_code, 302)
        page = self.client.get(reverse("accounts:login"))
        self.assertContains(page, 'lang="en"')
        self.assertContains(page, 'dir="ltr"')
        self.assertContains(page, "Create a new account")
        self.assertNotContains(page, "أنشئ حسابًا جديدًا")

    def test_switch_back_to_arabic(self):
        self.client.post(reverse("set_language"), {"language": "en", "next": "/"})
        self.client.post(reverse("set_language"), {"language": "ar", "next": "/"})
        self.assertContains(self.client.get(reverse("accounts:login")), 'dir="rtl"')

    def test_language_switch_button_is_on_the_page(self):
        self.assertContains(self.client.get(reverse("accounts:login")), reverse("accounts:save_language_preference"))
