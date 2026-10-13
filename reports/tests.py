from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.testing import make_category, make_payment, make_subscription, make_user

TODAY = timezone.localdate()


class ReportsTests(TestCase):
    """Known data -> known totals. Several payments per subscription must not inflate sums."""

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.cat_a = make_category("تقرير أ")
        self.cat_b = make_category("تقرير ب")
        d = lambda n: TODAY - timedelta(days=n)
        self.a1 = make_subscription(self.user, service_name="A1", category=self.cat_a, amount=Decimal("100"), next_renewal_date=TODAY + timedelta(days=5))
        self.a2 = make_subscription(self.user, service_name="A2", category=self.cat_a, amount=Decimal("120"), billing_cycle="yearly", next_renewal_date=TODAY + timedelta(days=50))
        self.b1 = make_subscription(self.user, service_name="B1", category=self.cat_b, amount=Decimal("10"), currency="USD", next_renewal_date=TODAY + timedelta(days=8))
        self.paused = make_subscription(self.user, service_name="P", category=self.cat_b, amount=Decimal("50"), status="paused", next_renewal_date=TODAY + timedelta(days=6))
        make_payment(self.user, self.a1, amount=Decimal("10"), payment_date=d(40))
        make_payment(self.user, self.a1, amount=Decimal("20"), payment_date=d(20))
        make_payment(self.user, self.a1, amount=Decimal("30"), payment_date=d(10))
        make_payment(self.user, self.a2, amount=Decimal("100"), payment_date=d(5))
        make_payment(self.user, self.b1, amount=Decimal("50"), payment_date=d(3))
        # must NOT be counted: failed, archived
        make_payment(self.user, self.a1, amount=Decimal("999"), payment_date=d(2), status="failed")
        make_payment(self.user, self.a1, amount=Decimal("500"), payment_date=d(1), is_archived=True)
        # another user's data must never leak in
        other = make_user("other@example.com")
        make_payment(other, make_subscription(other), amount=Decimal("7777"))

    def get(self, **params):
        response = self.client.get(reverse("reports:index"), params)
        self.assertEqual(response.status_code, 200)
        return response

    def totals(self, response):
        return {c["currency"]: (c["total"], c["count"]) for c in response.context["currency_totals"]}

    def test_currency_totals_are_separate_and_correct(self):
        totals = self.totals(self.get())
        self.assertEqual(totals["SAR"], (Decimal("160.00"), 4))
        self.assertEqual(totals["USD"], (Decimal("50.00"), 1))
        self.assertEqual(set(totals), {"SAR", "USD"})

    def test_per_subscription_totals_not_inflated(self):
        rows = {s.service_name: (s.total_paid, s.payments_n) for s in self.get().context["per_subscription"]}
        self.assertEqual(rows["A1"], (Decimal("60.00"), 3))
        self.assertEqual(rows["A2"], (Decimal("100.00"), 1))
        self.assertEqual(rows["B1"], (Decimal("50.00"), 1))
        self.assertNotIn("P", rows)

    def test_per_subscription_order_is_by_total_desc(self):
        names = [s.service_name for s in self.get().context["per_subscription"]]
        self.assertEqual(names, ["A2", "A1", "B1"])

    def test_category_counts_not_inflated_by_payments(self):
        stats = {c.name: c.total for c in self.get().context["category_stats"]}
        self.assertEqual(stats["تقرير أ"], 2)
        self.assertEqual(stats["تقرير ب"], 2)

    def test_status_counts(self):
        stats = {s["label"]: s["total"] for s in self.get().context["status_stats"]}
        self.assertEqual(stats["نشط"], 3)
        self.assertEqual(stats["متوقف"], 1)

    def test_monthly_estimate_is_per_currency_and_active_only(self):
        estimates = {m["currency"]: m["amount"] for m in self.get().context["monthly_estimates"]}
        self.assertEqual(estimates, {"SAR": Decimal("110.00"), "USD": Decimal("10.00")})

    def test_date_filter_applies_to_payments(self):
        response = self.get(date_from=(TODAY - timedelta(days=25)).isoformat(), date_to=TODAY.isoformat())
        self.assertEqual(self.totals(response)["SAR"], (Decimal("150.00"), 3))
        rows = {s.service_name: (s.total_paid, s.payments_n) for s in response.context["per_subscription"]}
        self.assertEqual(rows["A1"], (Decimal("50.00"), 2))

    def test_renewals_in_period(self):
        response = self.get(date_from=TODAY.isoformat(), date_to=(TODAY + timedelta(days=10)).isoformat())
        self.assertEqual(response.context["renewals_count"], 2)  # A1 (+5) and B1 (+8); paused P excluded

    def test_renewals_not_shown_without_period(self):
        self.assertIsNone(self.get().context["renewals_count"])

    def test_category_filter_applies_through_relationship(self):
        response = self.get(category=self.cat_a.pk)
        self.assertEqual(self.totals(response), {"SAR": (Decimal("160.00"), 4)})

    def test_subscription_filter(self):
        response = self.get(subscription=self.b1.pk)
        self.assertEqual(self.totals(response), {"USD": (Decimal("50.00"), 1)})

    def test_review_section(self):
        make_subscription(self.user, service_name="Late", next_renewal_date=TODAY - timedelta(days=4), start_date=TODAY - timedelta(days=90))
        names = [s.service_name for s in self.get().context["review_subs"]]
        self.assertEqual(names, ["Late"])

    def test_invalid_period_does_not_crash(self):
        response = self.get(date_from=TODAY.isoformat(), date_to=(TODAY - timedelta(days=3)).isoformat())
        self.assertEqual(response.status_code, 200)

    def test_empty_account_shows_friendly_message(self):
        self.client.force_login(make_user("empty@example.com"))
        response = self.get()
        self.assertContains(response, "لا توجد بيانات كافية")
        self.assertEqual(response.context["currency_totals"], [])

    def test_login_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("reports:index")).status_code, 302)
