from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from notifications.models import Notification
from payments.models import Payment
from subscriptions.models import Subscription
from subscriptions.services import monthly_cost_by_currency

from .theme import ONE_YEAR, THEME_COOKIE, THEMES


@login_required
def dashboard(request):
    """Section 1: live summary computed from the database (no fixed numbers)."""
    today = timezone.localdate()
    subs = Subscription.objects.filter(user=request.user)
    active = subs.filter(status=Subscription.Status.ACTIVE)

    # aggregate(): several conditional counts in one query
    stats = subs.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Subscription.Status.ACTIVE)),
        renewing_soon=Count(
            "id",
            filter=Q(
                status=Subscription.Status.ACTIVE,
                next_renewal_date__gte=today,
                next_renewal_date__lte=today + timedelta(days=7),
            ),
        ),
        needs_review=Count(
            "id",
            filter=Q(status=Subscription.Status.ACTIVE, next_renewal_date__lt=today),
        ),
    )

    upcoming = (
        active.filter(next_renewal_date__gte=today)
        .select_related("category")
        .order_by("next_renewal_date", "service_name")[:5]
    )
    latest_payments = (
        Payment.objects.filter(user=request.user, is_archived=False)
        .select_related("subscription")
        .order_by("-payment_date", "-pk")[:5]
    )
    latest_notifications = (
        Notification.objects.filter(user=request.user)
        .select_related("subscription")
        .order_by("-created_at", "-pk")[:5]
    )
    return render(
        request,
        "core/dashboard.html",
        {
            "stats": stats,
            "monthly_estimates": monthly_cost_by_currency(active),
            "upcoming": upcoming,
            "latest_payments": latest_payments,
            "latest_notifications": latest_notifications,
        },
    )


@require_POST
def set_theme(request):
    """Save the chosen theme in BOTH the session and a cookie (no JavaScript)."""
    chosen = request.POST.get("theme")
    if chosen not in THEMES:
        chosen = "light"
    target = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = "/"
    request.session["theme"] = chosen
    response = redirect(target)
    response.set_cookie(THEME_COOKIE, chosen, max_age=ONE_YEAR, samesite="Lax", httponly=True)
    return response
