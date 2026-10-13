from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.testing import make_category, make_payment, make_subscription, make_user

from .models import Category, Subscription
from .services import monthly_cost_by_currency
from .templatetags.service_tags import SERVICES, lookup


def form_data(**overrides):
    today = timezone.localdate()
    data = {
        "service_name": "Spotify",
        "category": make_category().pk,
        "amount": "22.00",
        "currency": "SAR",
        "billing_cycle": "monthly",
        "start_date": today.isoformat(),
        "next_renewal_date": (today + timedelta(days=30)).isoformat(),
        "status": "active",
        "is_recurring": "True",
        "reminder_days_before": "3",
        "notes": "",
    }
    data.update(overrides)
    return data


class SubscriptionCrudTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_anonymous_is_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("subscriptions:list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_create_saves_to_database(self):
        response = self.client.post(reverse("subscriptions:create"), form_data())
        sub = Subscription.objects.get()
        self.assertRedirects(response, reverse("subscriptions:detail", args=[sub.pk]))
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.service_name, "Spotify")
        self.assertEqual(sub.amount, Decimal("22.00"))
        self.assertTrue(sub.is_recurring)

    def test_create_non_recurring(self):
        self.client.post(reverse("subscriptions:create"), form_data(is_recurring="False"))
        self.assertFalse(Subscription.objects.get().is_recurring)

    def test_update_persists_changes(self):
        sub = make_subscription(self.user)
        data = form_data(service_name="Netflix Premium", amount="60.00", status="paused")
        response = self.client.post(reverse("subscriptions:update", args=[sub.pk]), data)
        self.assertEqual(response.status_code, 302)
        sub.refresh_from_db()
        self.assertEqual(sub.service_name, "Netflix Premium")
        self.assertEqual(sub.amount, Decimal("60.00"))
        self.assertEqual(sub.status, "paused")

    def test_negative_amount_rejected(self):
        response = self.client.post(reverse("subscriptions:create"), form_data(amount="-5"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("amount", response.context["form"].errors)
        self.assertFalse(Subscription.objects.exists())

    def test_missing_required_fields_rejected(self):
        for field in ("service_name", "category", "amount", "start_date", "next_renewal_date"):
            data = form_data()
            data[field] = ""
            response = self.client.post(reverse("subscriptions:create"), data)
            self.assertEqual(response.status_code, 200, field)
            self.assertIn(field, response.context["form"].errors, field)
        self.assertFalse(Subscription.objects.exists())

    def test_renewal_before_start_rejected(self):
        today = timezone.localdate()
        data = form_data(start_date=today.isoformat(), next_renewal_date=(today - timedelta(days=1)).isoformat())
        response = self.client.post(reverse("subscriptions:create"), data)
        self.assertIn("next_renewal_date", response.context["form"].errors)
        self.assertFalse(Subscription.objects.exists())

    def test_invalid_choices_rejected(self):
        for field, value in (("currency", "XXX"), ("billing_cycle", "daily"), ("status", "weird")):
            response = self.client.post(reverse("subscriptions:create"), form_data(**{field: value}))
            self.assertIn(field, response.context["form"].errors, field)

    def test_reminder_days_limit(self):
        response = self.client.post(reverse("subscriptions:create"), form_data(reminder_days_before="61"))
        self.assertIn("reminder_days_before", response.context["form"].errors)

    def test_database_rejects_negative_amount(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_subscription(self.user, amount=Decimal("-1"))

    def test_detail_shows_related_payments(self):
        sub = make_subscription(self.user)
        make_payment(self.user, sub, amount=Decimal("45.00"))
        response = self.client.get(reverse("subscriptions:detail", args=[sub.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["paid"]["count"], 1)
        self.assertEqual(response.context["paid"]["total"], Decimal("45.00"))


class DeleteArchiveTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_confirmation_page_is_shown_before_delete(self):
        sub = make_subscription(self.user)
        response = self.client.get(reverse("subscriptions:delete", args=[sub.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Subscription.objects.filter(pk=sub.pk).exists())

    def test_delete_without_payments_works(self):
        sub = make_subscription(self.user)
        self.client.post(reverse("subscriptions:delete", args=[sub.pk]))
        self.assertFalse(Subscription.objects.filter(pk=sub.pk).exists())

    def test_delete_with_payments_is_blocked(self):
        sub = make_subscription(self.user)
        make_payment(self.user, sub)
        response = self.client.post(reverse("subscriptions:delete", args=[sub.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Subscription.objects.filter(pk=sub.pk).exists())

    def test_archive_hides_from_default_list_but_keeps_record(self):
        sub = make_subscription(self.user)
        make_payment(self.user, sub)
        self.client.post(reverse("subscriptions:archive", args=[sub.pk]))
        sub.refresh_from_db()
        self.assertEqual(sub.status, "archived")
        self.assertEqual(sub.payments.count(), 1)
        response = self.client.get(reverse("subscriptions:list"))
        self.assertEqual(len(response.context["page_obj"].object_list), 0)
        response = self.client.get(reverse("subscriptions:list"), {"status": "archived"})
        self.assertEqual(len(response.context["page_obj"].object_list), 1)

    def test_archive_requires_post(self):
        sub = make_subscription(self.user)
        self.assertEqual(self.client.get(reverse("subscriptions:archive", args=[sub.pk])).status_code, 405)

    def test_category_cannot_be_deleted_while_used(self):
        from django.db.models import RestrictedError

        sub = make_subscription(self.user)
        with self.assertRaises(RestrictedError):
            sub.category.delete()


class OwnershipTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner@example.com")
        self.other = make_user("other@example.com")
        self.sub = make_subscription(self.owner)
        self.client.force_login(self.other)

    def test_other_users_cannot_open_edit_archive_or_delete(self):
        for name in ("detail", "update", "delete"):
            response = self.client.get(reverse(f"subscriptions:{name}", args=[self.sub.pk]))
            self.assertEqual(response.status_code, 404, name)
        self.assertEqual(self.client.post(reverse("subscriptions:archive", args=[self.sub.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("subscriptions:delete", args=[self.sub.pk])).status_code, 404)
        self.assertEqual(
            self.client.post(reverse("subscriptions:update", args=[self.sub.pk]), form_data()).status_code, 404
        )
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "active")

    def test_list_only_shows_own_records(self):
        mine = make_subscription(self.other, service_name="Mine")
        response = self.client.get(reverse("subscriptions:list"))
        self.assertEqual([s.pk for s in response.context["page_obj"]], [mine.pk])

    def test_missing_record_is_404_not_500(self):
        self.assertEqual(self.client.get(reverse("subscriptions:detail", args=[999999])).status_code, 404)


class FilterOrderPaginateTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        today = timezone.localdate()
        self.cat_a = make_category("تصنيف أ")
        self.cat_b = make_category("تصنيف ب")
        self.netflix = make_subscription(self.user, service_name="Netflix", amount=Decimal("45"), next_renewal_date=today + timedelta(days=10), category=self.cat_a)
        self.spotify = make_subscription(self.user, service_name="Spotify", amount=Decimal("22"), status="paused", next_renewal_date=today + timedelta(days=5), category=self.cat_b)
        self.canva = make_subscription(self.user, service_name="Canva", amount=Decimal("100"), billing_cycle="yearly", next_renewal_date=today + timedelta(days=40), category=self.cat_a)
        self.old = make_subscription(self.user, service_name="OldService", status="archived")

    def names(self, **params):
        response = self.client.get(reverse("subscriptions:list"), params)
        self.assertEqual(response.status_code, 200)
        return [s.service_name for s in response.context["page_obj"]]

    def test_default_excludes_archived_and_orders_by_renewal(self):
        self.assertEqual(self.names(), ["Spotify", "Netflix", "Canva"])

    def test_search_by_name(self):
        self.assertEqual(self.names(q="net"), ["Netflix"])

    def test_filter_by_status_category_cycle(self):
        self.assertEqual(self.names(status="paused"), ["Spotify"])
        self.assertEqual(self.names(status="archived"), ["OldService"])
        self.assertEqual(sorted(self.names(category=self.cat_a.pk)), ["Canva", "Netflix"])
        self.assertEqual(self.names(billing_cycle="yearly"), ["Canva"])

    def test_ordering_options(self):
        self.assertEqual(self.names(ordering="amount"), ["Spotify", "Netflix", "Canva"])
        self.assertEqual(self.names(ordering="-amount"), ["Canva", "Netflix", "Spotify"])
        self.assertEqual(self.names(ordering="-renewal"), ["Canva", "Netflix", "Spotify"])
        self.assertEqual(self.names(ordering="name"), ["Canva", "Netflix", "Spotify"])

    def test_no_results_message(self):
        response = self.client.get(reverse("subscriptions:list"), {"q": "zzzz"})
        self.assertContains(response, "لا توجد اشتراكات تطابق")

    def test_needs_review_filter(self):
        overdue = make_subscription(self.user, service_name="Overdue", next_renewal_date=timezone.localdate() - timedelta(days=3), start_date=timezone.localdate() - timedelta(days=90))
        self.assertEqual(self.names(review="on"), ["Overdue"])
        self.assertTrue(overdue.needs_review)

    def test_pagination(self):
        for i in range(10):
            make_subscription(self.user, service_name=f"Extra {i}")
        page1 = self.client.get(reverse("subscriptions:list"))
        self.assertEqual(len(page1.context["page_obj"].object_list), 10)
        page2 = self.client.get(reverse("subscriptions:list"), {"page": 2})
        self.assertEqual(len(page2.context["page_obj"].object_list), 3)
        bad = self.client.get(reverse("subscriptions:list"), {"page": "abc"})
        self.assertEqual(bad.status_code, 200)

    def test_empty_list_message(self):
        Subscription.objects.all().delete()
        response = self.client.get(reverse("subscriptions:list"))
        self.assertContains(response, "لم تضف أي اشتراك بعد")

    def test_invalid_filter_value_does_not_crash(self):
        response = self.client.get(reverse("subscriptions:list"), {"status": "nonsense", "category": "abc"})
        self.assertEqual(response.status_code, 200)


class MonthlyCostTests(TestCase):
    def test_monthly_estimate_per_currency_without_mixing(self):
        user = make_user()
        make_subscription(user, service_name="W", amount=Decimal("12"), billing_cycle="weekly")
        make_subscription(user, service_name="M", amount=Decimal("100"), billing_cycle="monthly")
        make_subscription(user, service_name="Q", amount=Decimal("90"), billing_cycle="quarterly")
        make_subscription(user, service_name="Y", amount=Decimal("120"), billing_cycle="yearly")
        make_subscription(user, service_name="U", amount=Decimal("5"), currency="USD")
        make_subscription(user, service_name="Paused", amount=Decimal("999"), status="paused")
        active = Subscription.objects.filter(user=user, status="active")
        self.assertEqual(
            monthly_cost_by_currency(active),
            [
                {"currency": "SAR", "amount": Decimal("192.00")},
                {"currency": "USD", "amount": Decimal("5.00")},
            ],
        )

    def test_empty_queryset_gives_empty_list(self):
        self.assertEqual(monthly_cost_by_currency(Subscription.objects.none()), [])


class CategoryAndIconTests(TestCase):
    def test_default_categories_exist_from_migration(self):
        self.assertTrue(Category.objects.filter(name="الذكاء الاصطناعي").exists())

    def test_category_name_unique_case_insensitive(self):
        Category.objects.create(name="Gadgets")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="gadgets")

    def test_thirty_known_services(self):
        self.assertEqual(len(SERVICES), 30)

    def test_lookup(self):
        self.assertEqual(lookup("Netflix"), "netflix")
        self.assertEqual(lookup("Disney+"), "disney")
        self.assertEqual(lookup("Apple TV+"), "appletv")
        self.assertEqual(lookup("claude"), "claude")
        self.assertIsNone(lookup("Some Random Service"))

    def render(self, name):
        return Template("{% load service_tags %}{% service_icon name %}").render(Context({"name": name}))

    def test_known_service_gets_badge_and_unknown_gets_globe(self):
        self.assertNotIn("svc-globe", self.render("ChatGPT"))
        self.assertIn("svc-globe", self.render("خدمة غير معروفة"))


class CategoryTranslationTests(TestCase):
    """Default categories are stored in Arabic and shown in the user's language; the database is not changed."""

    def test_default_category_name_is_translated_for_display_only(self):
        from django.utils import translation

        games = Category.objects.get(name="الألعاب")
        with translation.override("en"):
            self.assertEqual(games.display_name, "Games")
            self.assertEqual(str(games), "Games")
        with translation.override("ar"):
            self.assertEqual(games.display_name, "الألعاب")
        games.refresh_from_db()
        self.assertEqual(games.name, "الألعاب")

    def test_custom_category_name_is_never_changed(self):
        from django.utils import translation

        mine = Category.objects.create(name="My own group")
        with translation.override("en"):
            self.assertEqual(mine.display_name, "My own group")

    def test_english_user_sees_english_category_names_in_list_and_filters(self):
        user = make_user()
        user.profile.preferred_language = "en"
        user.profile.save()
        make_subscription(user, category=Category.objects.get(name="الألعاب"))
        self.client.force_login(user)
        page = self.client.get(reverse("subscriptions:list"))
        self.assertContains(page, "Games")
        self.assertContains(page, "Artificial Intelligence")
        self.assertNotContains(page, "الذكاء الاصطناعي")

    def test_arabic_user_still_sees_arabic_category_names(self):
        user = make_user()
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("subscriptions:list")), "الذكاء الاصطناعي")
