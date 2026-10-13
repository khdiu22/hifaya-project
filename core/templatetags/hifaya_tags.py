from django.utils.translation import gettext_lazy as _
from datetime import date
from decimal import Decimal, InvalidOperation

from django import template
from django.utils import timezone

register = template.Library()

SYMBOLS = {"SAR": _("ر.س"), "USD": "$", "EUR": "€", "GBP": "£", "AED": _("د.إ")}

BADGES = {
    "active": "badge-active",
    "paused": "badge-paused",
    "cancelled": "badge-cancelled",
    "archived": "badge-archived",
    "paid": "badge-active",
    "pending": "badge-paused",
    "failed": "badge-cancelled",
    "refunded": "badge-review",
}


@register.filter
def money(amount, currency=""):
    """45 -> '45.00 ر.س' (never mixes currencies; always shows its own symbol)."""
    if amount is None or amount == "":
        return "—"
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        return str(amount)
    return f"{value:,.2f} {SYMBOLS.get(currency, currency)}".strip()


@register.filter
def renewal_text(value):
    """Easy-to-read relative date, e.g. 'بعد 3 أيام'."""
    if not isinstance(value, date):
        return "—"
    days = (value - timezone.localdate()).days
    if days == 0:
        return _("اليوم")
    if days == 1:
        return _("غدًا")
    if days == 2:
        return _("بعد يومين")
    if 3 <= days <= 10:
        return _("بعد %(days)s أيام") % {"days": days}
    if days > 10:
        return _("بعد %(days)s يومًا") % {"days": days}
    if days == -1:
        return _("أمس (متأخر)")
    return _("متأخر منذ %(v1)s يومًا") % {"v1": -days}


@register.filter
def badge(value):
    return BADGES.get(value, "badge-review")
