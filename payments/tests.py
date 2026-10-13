import json
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.testing import make_payment, make_subscription, make_user

from .importer import parse_payments_json
from .models import Payment

TODAY = timezone.localdate()


def form_data(sub=None, **overrides):
    data = {
        "subscription": sub.pk if sub else "",
        "amount": "45.00",
        "currency": "SAR",
        "payment_date": TODAY.isoformat(),
        "payment_method": "Card",
        "reference": "R1",
        "status": "paid",
        "notes": "",
    }
    data.update(overrides)
    return data


class PaymentCrudTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.sub = make_subscription(self.user)

    def test_create_linked_to_own_subscription(self):
        response = self.client.post(reverse("payments:create"), form_data(self.sub))
        payment = Payment.objects.get()
        self.assertRedirects(response, reverse("payments:detail", args=[payment.pk]))
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.subscription, self.sub)

    def test_create_without_subscription_is_allowed(self):
        self.client.post(reverse("payments:create"), form_data())
        self.assertIsNone(Payment.objects.get().subscription)

    def test_cannot_link_to_someone_elses_subscription(self):
        other_sub = make_subscription(make_user("other@example.com"))
        response = self.client.post(reverse("payments:create"), form_data(other_sub))
        self.assertEqual(response.status_code, 200)
        self.assertIn("subscription", response.context["form"].errors)
        self.assertFalse(Payment.objects.exists())

    def test_negative_and_missing_values_rejected(self):
        response = self.client.post(reverse("payments:create"), form_data(self.sub, amount="-1"))
        self.assertIn("amount", response.context["form"].errors)
        response = self.client.post(reverse("payments:create"), form_data(self.sub, amount=""))
        self.assertIn("amount", response.context["form"].errors)
        response = self.client.post(reverse("payments:create"), form_data(self.sub, payment_date=""))
        self.assertIn("payment_date", response.context["form"].errors)
        self.assertFalse(Payment.objects.exists())

    def test_currency_must_match_subscription(self):
        response = self.client.post(reverse("payments:create"), form_data(self.sub, currency="USD"))
        self.assertIn("currency", response.context["form"].errors)
        self.assertFalse(Payment.objects.exists())

    def test_update_persists(self):
        payment = make_payment(self.user, self.sub)
        response = self.client.post(
            reverse("payments:update", args=[payment.pk]), form_data(self.sub, amount="50.00", reference="NEW")
        )
        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal("50.00"))
        self.assertEqual(payment.reference, "NEW")

    def test_other_user_gets_404(self):
        payment = make_payment(make_user("other@example.com"))
        for name in ("detail", "update", "delete"):
            self.assertEqual(self.client.get(reverse(f"payments:{name}", args=[payment.pk])).status_code, 404, name)
        for name in ("archive", "restore", "reviewed", "delete"):
            self.assertEqual(self.client.post(reverse(f"payments:{name}", args=[payment.pk])).status_code, 404, name)

    def test_archive_restore_and_delete_rules(self):
        payment = make_payment(self.user, self.sub)
        # active payments cannot be deleted
        self.client.post(reverse("payments:delete", args=[payment.pk]))
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())
        # archive hides it from the default list
        self.client.post(reverse("payments:archive", args=[payment.pk]))
        payment.refresh_from_db()
        self.assertTrue(payment.is_archived)
        self.assertEqual(len(self.client.get(reverse("payments:list")).context["page_obj"].object_list), 0)
        # archived payments cannot be edited
        self.assertEqual(self.client.get(reverse("payments:update", args=[payment.pk])).status_code, 302)
        # restore works
        self.client.post(reverse("payments:restore", args=[payment.pk]))
        payment.refresh_from_db()
        self.assertFalse(payment.is_archived)
        # archived payments can be deleted after confirmation
        self.client.post(reverse("payments:archive", args=[payment.pk]))
        self.assertEqual(self.client.get(reverse("payments:delete", args=[payment.pk])).status_code, 200)
        self.client.post(reverse("payments:delete", args=[payment.pk]))
        self.assertFalse(Payment.objects.filter(pk=payment.pk).exists())

    def test_payment_does_not_block_subscription_archiving(self):
        make_payment(self.user, self.sub)
        self.client.post(reverse("subscriptions:archive", args=[self.sub.pk]))
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, "archived")
        self.assertEqual(self.sub.payments.count(), 1)


class PaymentFilterTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.a = make_subscription(self.user, service_name="A")
        self.b = make_subscription(self.user, service_name="B")
        self.p1 = make_payment(self.user, self.a, amount=Decimal("10"), payment_date=TODAY - timedelta(days=40))
        self.p2 = make_payment(self.user, self.a, amount=Decimal("20"), payment_date=TODAY - timedelta(days=20), status="failed")
        self.p3 = make_payment(self.user, self.b, amount=Decimal("30"), payment_date=TODAY - timedelta(days=10))
        self.p4 = make_payment(self.user, None, amount=Decimal("99"), payment_date=TODAY - timedelta(days=1), review_required=True, review_reason="x")

    def ids(self, **params):
        response = self.client.get(reverse("payments:list"), params)
        self.assertEqual(response.status_code, 200)
        return [p.pk for p in response.context["page_obj"]]

    def test_default_order_newest_first(self):
        self.assertEqual(self.ids(), [self.p4.pk, self.p3.pk, self.p2.pk, self.p1.pk])

    def test_filter_by_subscription_status_dates_review(self):
        self.assertEqual(self.ids(subscription=self.b.pk), [self.p3.pk])
        self.assertEqual(self.ids(status="failed"), [self.p2.pk])
        self.assertEqual(self.ids(date_from=(TODAY - timedelta(days=25)).isoformat()), [self.p4.pk, self.p3.pk, self.p2.pk])
        self.assertEqual(self.ids(date_to=(TODAY - timedelta(days=25)).isoformat()), [self.p1.pk])
        self.assertEqual(self.ids(review="on"), [self.p4.pk])

    def test_ordering_by_amount(self):
        self.assertEqual(self.ids(ordering="amount"), [self.p1.pk, self.p2.pk, self.p3.pk, self.p4.pk])
        self.assertEqual(self.ids(ordering="-amount"), [self.p4.pk, self.p3.pk, self.p2.pk, self.p1.pk])

    def test_no_results_message(self):
        response = self.client.get(reverse("payments:list"), {"status": "refunded"})
        self.assertContains(response, "لا توجد مدفوعات تطابق")

    def test_empty_state(self):
        Payment.objects.all().delete()
        self.assertContains(self.client.get(reverse("payments:list")), "لا توجد مدفوعات مسجّلة بعد")

    def test_invalid_date_range_is_ignored_safely(self):
        response = self.client.get(
            reverse("payments:list"), {"date_from": TODAY.isoformat(), "date_to": (TODAY - timedelta(days=5)).isoformat()}
        )
        self.assertEqual(response.status_code, 200)

    def test_other_users_payments_never_listed(self):
        make_payment(make_user("other@example.com"))
        self.assertEqual(len(self.ids()), 4)


class SimilarPaymentTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.sub = make_subscription(self.user)

    def post(self, **overrides):
        return self.client.post(reverse("payments:create"), form_data(self.sub, **overrides))

    def test_close_similar_payments_are_flagged_but_not_deleted(self):
        self.post(payment_date=(TODAY - timedelta(days=2)).isoformat())
        self.post(payment_date=TODAY.isoformat())
        self.assertEqual(Payment.objects.count(), 2)
        self.assertEqual(Payment.objects.filter(review_required=True).count(), 2)
        self.assertTrue(all(p.review_reason for p in Payment.objects.all()))

    def test_far_apart_or_different_amount_not_flagged(self):
        self.post(payment_date=(TODAY - timedelta(days=30)).isoformat())
        self.post(payment_date=TODAY.isoformat())
        self.post(payment_date=TODAY.isoformat(), amount="46.00")
        self.assertEqual(Payment.objects.count(), 3)
        self.assertFalse(Payment.objects.filter(review_required=True).exists())

    def test_other_users_do_not_trigger_flags(self):
        other = make_user("other@example.com")
        make_payment(other, make_subscription(other), amount=Decimal("45.00"))
        self.post()
        self.assertFalse(Payment.objects.filter(review_required=True).exists())

    def test_mark_reviewed_clears_flag(self):
        self.post(payment_date=(TODAY - timedelta(days=1)).isoformat())
        self.post()
        flagged = Payment.objects.filter(review_required=True).first()
        self.client.post(reverse("payments:reviewed", args=[flagged.pk]))
        flagged.refresh_from_db()
        self.assertFalse(flagged.review_required)
        self.assertEqual(flagged.review_reason, "")
        self.assertEqual(Payment.objects.count(), 2)


class JsonImportTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.sub = make_subscription(self.user)
        self.url = reverse("payments:import")

    def upload(self, payload, as_text=False):
        raw = payload.encode() if as_text else json.dumps(payload).encode()
        return self.client.post(self.url, {"file": SimpleUploadedFile("p.json", raw, content_type="application/json")})

    def row(self, **overrides):
        data = {"subscription_id": self.sub.pk, "amount": "45.00", "currency": "SAR", "payment_date": TODAY.isoformat(), "status": "paid"}
        data.update(overrides)
        return data

    def test_valid_file_is_imported(self):
        response = self.upload({"payments": [self.row(payment_date=(TODAY - timedelta(days=40)).isoformat()), self.row(amount="12.50", subscription_id=None)]})
        self.assertRedirects(response, reverse("payments:list"))
        self.assertEqual(Payment.objects.filter(user=self.user).count(), 2)

    def test_invalid_json_is_rejected_cleanly(self):
        response = self.upload("{not json", as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["errors"])
        self.assertFalse(Payment.objects.exists())

    def test_one_bad_row_saves_nothing(self):
        response = self.upload({"payments": [self.row(), self.row(amount="-5")]})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Payment.objects.exists())

    def test_row_validation_errors(self):
        bad_rows = [
            self.row(amount="abc"),
            self.row(amount="10.123"),
            self.row(currency="XXX"),
            self.row(payment_date="31/12/2026"),
            self.row(status="weird"),
            self.row(subscription_id="1"),
            self.row(currency="USD"),  # does not match the subscription currency
            "not an object",
        ]
        for bad in bad_rows:
            rows, errors = parse_payments_json(json.dumps({"payments": [bad]}).encode(), self.user)
            self.assertTrue(errors, bad)
            self.assertEqual(rows, [], bad)

    def test_other_users_subscription_is_rejected(self):
        other_sub = make_subscription(make_user("other@example.com"))
        response = self.upload({"payments": [self.row(subscription_id=other_sub.pk)]})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Payment.objects.exists())

    def test_structure_errors(self):
        for payload in ([], {"payments": "x"}, {"payments": []}, {"other": 1}):
            _rows, errors = parse_payments_json(json.dumps(payload).encode(), self.user)
            self.assertTrue(errors, payload)

    def test_similar_rows_in_file_are_flagged_not_deleted(self):
        self.upload({"payments": [self.row(), self.row()]})
        self.assertEqual(Payment.objects.count(), 2)
        self.assertEqual(Payment.objects.filter(review_required=True).count(), 2)

    def test_no_file_selected(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Payment.objects.exists())
