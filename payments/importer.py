"""Validation and import of the documented Hifaya JSON payment format (see docs/JSON_IMPORT.md).

Nothing is saved unless EVERY row is valid; saving happens in one transaction.
"""
from django.utils.translation import gettext_lazy as _
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from subscriptions.models import Currency, Subscription

from .models import Payment
from .services import flag_similar

MAX_BYTES = 1_000_000
MAX_ROWS = 500
MAX_ERRORS_SHOWN = 20


def _validate_row(index, item, user_subs):
    errors, row = [], {}
    label = _("العنصر %(index)s") % {"index": index}
    if not isinstance(item, dict):
        return [_("%(label)s: يجب أن يكون كائنًا (object).") % {"label": label}], None

    # amount
    raw = item.get("amount")
    if raw is None or isinstance(raw, bool) or raw == "":
        errors.append(_("%(label)s: الحقل amount مطلوب.") % {"label": label})
    else:
        try:
            amount = Decimal(str(raw).strip())
            if not amount.is_finite():
                raise InvalidOperation
        except InvalidOperation:
            errors.append(_("%(label)s: قيمة amount غير رقمية.") % {"label": label})
        else:
            if amount < 0:
                errors.append(_("%(label)s: لا يُسمح بمبلغ سالب.") % {"label": label})
            elif amount.as_tuple().exponent < -2:
                errors.append(_("%(label)s: amount يقبل خانتين عشريتين كحد أقصى.") % {"label": label})
            elif amount >= Decimal("100000000"):
                errors.append(_("%(label)s: قيمة amount كبيرة جدًا.") % {"label": label})
            else:
                row["amount"] = amount

    # currency
    currency = item.get("currency")
    if currency not in Currency.values:
        errors.append(_("%(label)s: العملة غير مدعومة (%(v2)s).") % {"label": label, "v2": ', '.join(Currency.values)})
    else:
        row["currency"] = currency

    # payment_date
    raw_date = item.get("payment_date")
    try:
        if not isinstance(raw_date, str):
            raise ValueError
        row["payment_date"] = date.fromisoformat(raw_date)
    except ValueError:
        errors.append(_("%(label)s: payment_date مطلوب بصيغة YYYY-MM-DD.") % {"label": label})

    # status (optional, default paid)
    status = item.get("status", Payment.Status.PAID)
    if status not in Payment.Status.values:
        errors.append(_("%(label)s: status يجب أن يكون واحدًا من %(v2)s.") % {"label": label, "v2": ', '.join(Payment.Status.values)})
    else:
        row["status"] = status

    # optional text fields
    for key, limit in (("payment_method", 50), ("reference", 100), ("notes", 1000)):
        value = item.get(key, "")
        if value is None:
            value = ""
        if not isinstance(value, str) or len(value) > limit:
            errors.append(_("%(label)s: الحقل %(key)s يجب أن يكون نصًا لا يتجاوز %(limit)s حرفًا.") % {"label": label, "key": key, "limit": limit})
        else:
            row[key] = value.strip()

    # subscription link (optional) - must belong to the same user
    sub_id = item.get("subscription_id")
    if sub_id is not None:
        if isinstance(sub_id, bool) or not isinstance(sub_id, int):
            errors.append(_("%(label)s: subscription_id يجب أن يكون رقمًا صحيحًا أو null.") % {"label": label})
        elif sub_id not in user_subs:
            errors.append(_("%(label)s: الاشتراك رقم %(sub_id)s غير موجود في حسابك.") % {"label": label, "sub_id": sub_id})
        else:
            subscription = user_subs[sub_id]
            if row.get("currency") and subscription.currency != row["currency"]:
                errors.append(_("%(label)s: عملة الدفعة لا تطابق عملة الاشتراك (%(currency)s).") % {"label": label, "currency": subscription.currency})
            row["subscription"] = subscription
    return errors, row


def parse_payments_json(raw_bytes, user):
    """Return (rows, errors). Rows are only usable when errors is empty."""
    if len(raw_bytes) > MAX_BYTES:
        return [], [_("حجم الملف أكبر من الحد المسموح (1 ميغابايت).")]
    try:
        data = json.loads(raw_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [], [_("الملف ليس JSON صالحًا (تأكد من الترميز UTF-8 ومن صحة الأقواس والفواصل).")]
    if not isinstance(data, dict) or not isinstance(data.get("payments"), list):
        return [], [_('يجب أن يحتوي الملف على كائن فيه قائمة باسم "payments".')]
    items = data["payments"]
    if not items:
        return [], [_("قائمة payments فارغة.")]
    if len(items) > MAX_ROWS:
        return [], [_("عدد الدفعات يتجاوز الحد المسموح (%(MAX_ROWS)s).") % {"MAX_ROWS": MAX_ROWS}]

    user_subs = {sub.pk: sub for sub in Subscription.objects.filter(user=user)}
    rows, errors = [], []
    for index, item in enumerate(items, start=1):
        row_errors, row = _validate_row(index, item, user_subs)
        errors.extend(row_errors)
        if not row_errors:
            rows.append(row)
    return rows, errors


def import_rows(rows, user):
    """Save all rows atomically. Returns (created_count, flagged_count)."""
    created = flagged = 0
    with transaction.atomic():
        for row in rows:
            payment = Payment(user=user, **row)
            payment.full_clean()
            payment.save()
            if flag_similar(payment):
                flagged += 1
            created += 1
    return created, flagged


def safe_import(raw_bytes, user):
    """High level helper used by the view. Returns (created, flagged, errors)."""
    rows, errors = parse_payments_json(raw_bytes, user)
    if errors:
        return 0, 0, errors
    try:
        created, flagged = import_rows(rows, user)
    except ValidationError as exc:
        return 0, 0, [_("فشل التحقق أثناء الحفظ، ولم يُحفظ شيء: %(v1)s") % {"v1": '; '.join(exc.messages)}]
    return created, flagged, []
