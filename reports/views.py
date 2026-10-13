
"""Section 5: reports. Every figure is computed by the database through the ORM
(aggregate() / annotate()); currencies are never added together.
"""

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from payments.models import Payment
from subscriptions.models import Category, Currency, Subscription
from subscriptions.services import monthly_cost_by_currency

from .forms import ReportFilterForm


@login_required
def report(request):
    form = ReportFilterForm(request.GET, user=request.user)
    data = form.cleaned_data if form.is_valid() else {}
    today = timezone.localdate()
    date_from, date_to = data.get("date_from"), data.get("date_to")

    # Show only the current user's subscriptions and payments.
    subs = Subscription.objects.filter(user=request.user)
    payments = Payment.objects.filter(
        user=request.user,
        is_archived=False,
    )

    if data.get("status"):
        subs = subs.filter(status=data["status"])
        payments = payments.filter(subscription__status=data["status"])

    if data.get("category"):
        subs = subs.filter(category=data["category"])
        payments = payments.filter(subscription__category=data["category"])

    if data.get("subscription"):
        subs = subs.filter(pk=data["subscription"].pk)
        payments = payments.filter(subscription=data["subscription"])

    if date_from:
        payments = payments.filter(payment_date__gte=date_from)

    if date_to:
        payments = payments.filter(payment_date__lte=date_to)

    # 1. Subscriptions by status.
    status_labels = dict(Subscription.Status.choices)
    status_stats = [
        {
            "label": status_labels.get(row["status"], row["status"]),
            "total": row["total"],
        }
        for row in (
            subs.order_by()
            .values("status")
            .annotate(total=Count("id"))
            .order_by("status")
        )
    ]

    # 2. Subscriptions per category.
    category_stats = (
        Category.objects.annotate(
            total=Count(
                "subscriptions",
                filter=Q(subscriptions__in=subs.values("pk")),
            )
        )
        .filter(total__gt=0)
        .order_by("-total", "name")
    )

    # 3. Paid totals per currency.
    paid = Q(status=Payment.Status.PAID)
    aggregates = {
        "payments_count": Count("id"),
        "paid_count": Count("id", filter=paid),
    }

    for code in Currency.values:
        aggregates[f"total_{code}"] = Sum(
            "amount",
            filter=paid & Q(currency=code),
        )
        aggregates[f"count_{code}"] = Count(
            "id",
            filter=paid & Q(currency=code),
        )

    totals = payments.aggregate(**aggregates)

    currency_totals = [
        {
            "currency": code,
            "label": Currency(code).label,
            "total": totals[f"total_{code}"],
            "count": totals[f"count_{code}"],
        }
        for code in Currency.values
        if totals[f"count_{code}"]
    ]

    # 4. Total paid per subscription.
    pay_filter = Q(
        payments__is_archived=False,
        payments__status=Payment.Status.PAID,
    )

    if date_from:
        pay_filter &= Q(payments__payment_date__gte=date_from)

    if date_to:
        pay_filter &= Q(payments__payment_date__lte=date_to)

    per_subscription = (
        subs.annotate(
            total_paid=Sum("payments__amount", filter=pay_filter),
            payments_n=Count("payments", filter=pay_filter),
        )
        .filter(payments_n__gt=0)
        .order_by("-total_paid", "service_name")
    )

    # 5. Renewals in the selected period.
    renewals_count = None

    if date_from or date_to:
        renew_q = Q(status=Subscription.Status.ACTIVE)

        if date_from:
            renew_q &= Q(next_renewal_date__gte=date_from)

        if date_to:
            renew_q &= Q(next_renewal_date__lte=date_to)

        renewals_count = subs.aggregate(
            n=Count("id", filter=renew_q)
        )["n"]

    # 6. Estimated monthly cost of active subscriptions.
    monthly_estimates = monthly_cost_by_currency(
        subs.filter(status=Subscription.Status.ACTIVE)
    )

    # 7. Items that need review.
    review_subs = (
        subs.filter(
            status=Subscription.Status.ACTIVE,
            next_renewal_date__lt=today,
        )
        .select_related("category")
        .order_by("next_renewal_date")
    )

    review_payments_count = payments.aggregate(
        n=Count("id", filter=Q(review_required=True))
    )["n"]

    has_data = (
        Subscription.objects.filter(user=request.user).exists()
        or Payment.objects.filter(user=request.user).exists()
    )

    return render(
        request,
        "reports/report.html",
        {
            "form": form,
            "has_data": has_data,
            "status_stats": status_stats,
            "category_stats": category_stats,
            "currency_totals": currency_totals,
            "payments_count": totals["payments_count"],
            "per_subscription": per_subscription,
            "renewals_count": renewals_count,
            "monthly_estimates": monthly_estimates,
            "review_subs": review_subs,
            "review_payments_count": review_payments_count,
            "period_chosen": bool(date_from or date_to),
        },
    )