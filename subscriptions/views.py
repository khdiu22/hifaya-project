from django.utils.translation import gettext_lazy as _
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.utils import paginate
from notifications.models import Notification

from .forms import SubscriptionFilterForm, SubscriptionForm
from .models import Subscription

ORDERING_MAP = {
    "renewal": ("next_renewal_date", "service_name"),
    "-renewal": ("-next_renewal_date", "service_name"),
    "amount": ("amount", "service_name"),
    "-amount": ("-amount", "service_name"),
    "name": ("service_name",),
    "-name": ("-service_name",),
}


def _own_subscription_or_404(request, pk):
    """Ownership check on the server: other users' records simply do not exist."""
    return get_object_or_404(Subscription.objects.select_related("category"), pk=pk, user=request.user)


@login_required
def subscription_list(request):
    form = SubscriptionFilterForm(request.GET)
    if form.is_valid():
        data = form.cleaned_data
    else:
        data = {}
        messages.warning(request, _("⚠️ بعض عوامل التصفية غير صالحة وتم تجاهلها."))

    qs = (
        Subscription.objects.filter(user=request.user)
        .select_related("category")
        .annotate(payments_count=Count("payments"))
    )
    if data.get("q"):
        qs = qs.filter(service_name__icontains=data["q"])
    if data.get("status"):
        qs = qs.filter(status=data["status"])
    else:
        qs = qs.exclude(status=Subscription.Status.ARCHIVED)
    if data.get("category"):
        qs = qs.filter(category=data["category"])
    if data.get("billing_cycle"):
        qs = qs.filter(billing_cycle=data["billing_cycle"])
    if data.get("review"):
        qs = qs.filter(status=Subscription.Status.ACTIVE, next_renewal_date__lt=timezone.localdate())
    qs = qs.order_by(*ORDERING_MAP.get(data.get("ordering") or "renewal", ORDERING_MAP["renewal"]))

    return render(
        request,
        "subscriptions/list.html",
        {
            "form": form,
            "page_obj": paginate(request, qs),
            "has_filters": any(data.get(key) for key in ("q", "status", "category", "billing_cycle", "review")),
            "has_any": Subscription.objects.filter(user=request.user).exists(),
        },
    )


@login_required
def subscription_detail(request, pk):
    sub = _own_subscription_or_404(request, pk)
    payments = sub.payments.filter(is_archived=False).order_by("-payment_date", "-pk")
    paid = payments.aggregate(
        total=Sum("amount", filter=Q(status="paid")),
        count=Count("id"),
    )
    return render(
        request,
        "subscriptions/detail.html",
        {
            "sub": sub,
            "payments": payments[:10],
            "paid": paid,
            "notifications": Notification.objects.filter(user=request.user, subscription=sub).order_by(
                "-created_at", "-pk"
            )[:5],
        },
    )


@login_required
def subscription_create(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.user = request.user
            sub.save()
            messages.success(request, _("✅ تم حفظ اشتراك «%(service_name)s» بنجاح!") % {"service_name": sub.service_name})
            return redirect("subscriptions:detail", pk=sub.pk)
        messages.error(request, _("❌ لم يتم الحفظ، راجع الحقول المظللة وصحّح الأخطاء."))
    else:
        today = timezone.localdate()
        form = SubscriptionForm(
            initial={
                "start_date": today,
                "next_renewal_date": today + timedelta(days=30),
                "reminder_days_before": 3,
                "currency": "SAR",
                "billing_cycle": "monthly",
                "status": "active",
                "is_recurring": "True",
            }
        )
    return render(request, "subscriptions/form.html", {"form": form, "title": _("إضافة اشتراك"), "is_edit": False})


@login_required
def subscription_update(request, pk):
    sub = _own_subscription_or_404(request, pk)
    if request.method == "POST":
        form = SubscriptionForm(request.POST, instance=sub)
        if form.is_valid():
            form.save()
            messages.success(request, _("✅ تم تحديث اشتراك «%(service_name)s».") % {"service_name": sub.service_name})
            return redirect("subscriptions:detail", pk=sub.pk)
        messages.error(request, _("❌ لم يتم الحفظ، راجع الحقول المظللة وصحّح الأخطاء."))
    else:
        form = SubscriptionForm(instance=sub)
    return render(
        request,
        "subscriptions/form.html",
        {"form": form, "title": _("تعديل اشتراك: %(service_name)s") % {"service_name": sub.service_name}, "is_edit": True, "sub": sub},
    )


@login_required
@require_POST
def subscription_archive(request, pk):
    sub = _own_subscription_or_404(request, pk)
    if sub.status == Subscription.Status.ARCHIVED:
        messages.info(request, _("💡 هذا الاشتراك مؤرشف مسبقًا."))
    else:
        sub.status = Subscription.Status.ARCHIVED
        sub.save(update_fields=["status", "updated_at"])
        messages.success(request, _("📦 تمت أرشفة «%(service_name)s». لن تصلك تذكيرات عنه، ويمكنك استعادته بتعديل حالته.") % {"service_name": sub.service_name})
    return redirect("subscriptions:list")


@login_required
def subscription_delete(request, pk):
    """Safe delete: allowed only when the subscription has no payments."""
    sub = _own_subscription_or_404(request, pk)
    payments_count = sub.payments.count()
    if request.method == "POST":
        if payments_count:
            messages.error(request, _("🚫 لا يمكن حذف اشتراك له مدفوعات مسجّلة، استخدم الأرشفة بدلًا من ذلك."))
            return redirect("subscriptions:detail", pk=sub.pk)
        name = sub.service_name
        sub.delete()
        messages.success(request, _("🗑️ تم حذف اشتراك «%(name)s» نهائيًا.") % {"name": name})
        return redirect("subscriptions:list")
    return render(
        request,
        "subscriptions/confirm_delete.html",
        {"sub": sub, "payments_count": payments_count},
    )
