from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Sum

# How many billing periods fit in one month.
MONTHLY_FACTORS = {
    "weekly": Decimal("52") / Decimal("12"),
    "monthly": Decimal("1"),
    "quarterly": Decimal("1") / Decimal("3"),
    "yearly": Decimal("1") / Decimal("12"),
}
TWO_PLACES = Decimal("0.01")


def monthly_cost_by_currency(queryset):
    """Estimated monthly cost of the given subscriptions, one total per currency.

    The database groups and sums the amounts (annotate + Sum) per currency and
    billing cycle; only those few grouped totals are scaled to a monthly value.
    Currencies are never mixed and no exchange rate is assumed.
    """
    grouped = (
        queryset.order_by()
        .values("currency", "billing_cycle")
        .annotate(total=Sum("amount"))
        .order_by("currency", "billing_cycle")
    )
    totals = {}
    for row in grouped:
        factor = MONTHLY_FACTORS.get(row["billing_cycle"], Decimal("0"))
        totals[row["currency"]] = totals.get(row["currency"], Decimal("0")) + row["total"] * factor
    return [
        {"currency": currency, "amount": amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)}
        for currency, amount in sorted(totals.items())
    ]
