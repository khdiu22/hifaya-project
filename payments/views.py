from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import paginate

from .forms import ImportForm, PaymentFilterForm, PaymentForm
from .importer import MAX_ERRORS_SHOWN, MAX_BYTES, safe_import
from .models import Payment
from .services import flag_similar

ORDERING_MAP = {
    "-date": ("-payment_date", "-id"),
    "date": ("payment_date", "id"),
    "-amount": ("-amount", "-id"),
    "amount": ("amount", "id"),
}


def _own_payment_or_404(request, pk):
    return get_object_or_404(Payment.objects.select_related("subscription"), pk=pk, user=request.user)


@login_required
def payment_list(request):
    form = PaymentFilterForm(request.GET, user=request.user)
    if form.is_valid():
        data = form.cleaned_data
    else:
        data = {}
        messages.warning(request, _("⚠️ بعض عوامل التصفية غير صالحة وتم تجاهلها."))

    qs = Payment.objects.filter(user=request.user).select_related("subscription")
    show = data.get("show") or "active"
    if show == "active":
        qs = qs.filter(is_archived=False)
    elif show == "archived":
        qs = qs.filter(is_archived=True)
    if data.get("subscription"):
        qs = qs.filter(subscription=data["subscription"])
    if data.get("status"):
        qs = qs.filter(status=data["status"])
    if data.get("date_from"):
        qs = qs.filter(payment_date__gte=data["date_from"])
    if data.get("date_to"):
        qs = qs.filter(payment_date__lte=data["date_to"])
    if data.get("review"):
        qs = qs.filter(review_required=True)
    qs = qs.order_by(*ORDERING_MAP.get(data.get("ordering") or "-date", ORDERING_MAP["-date"]))

    return render(
        request,
        "payments/list.html",
        {
            "form": form,
            "page_obj": paginate(request, qs),
            "has_filters": any(
                data.get(k) for k in ("subscription", "status", "date_from", "date_to", "review")
            )
            or show != "active",
            "has_any": Payment.objects.filter(user=request.user).exists(),
            "review_count": Payment.objects.filter(user=request.user, is_archived=False, review_required=True).count(),
        },
    )


@login_required
def payment_detail(request, pk):
    return render(request, "payments/detail.html", {"payment": _own_payment_or_404(request, pk)})


@login_required
def payment_create(request):
    if request.method == "POST":
        form = PaymentForm(request.POST, user=request.user)
        if form.is_valid():
            payment = form.save()
            if flag_similar(payment):
                messages.warning(request, _("🔎 تم حفظ الدفعة، وهي تشبه دفعة أخرى فوُضعت علامة «تحتاج إلى مراجعة»."))
            else:
                messages.success(request, _("✅ تم تسجيل الدفعة بنجاح!"))
            return redirect("payments:detail", pk=payment.pk)
        messages.error(request, _("❌ لم يتم الحفظ، راجع الحقول المظللة وصحّح الأخطاء."))
    else:
        initial = {}
        subscription_id = request.GET.get("subscription")
        if subscription_id and subscription_id.isdigit():
            from subscriptions.models import Subscription

            sub = Subscription.objects.filter(pk=int(subscription_id), user=request.user).first()
            if sub:
                initial = {"subscription": sub, "amount": sub.amount, "currency": sub.currency}
        form = PaymentForm(user=request.user, initial=initial)
    return render(request, "payments/form.html", {"form": form, "title": _("تسجيل دفعة"), "is_edit": False})


@login_required
def payment_update(request, pk):
    payment = _own_payment_or_404(request, pk)
    if payment.is_archived:
        messages.info(request, _("💡 هذه الدفعة مؤرشفة؛ استعدها أولًا إذا أردت تعديلها."))
        return redirect("payments:detail", pk=payment.pk)
    if request.method == "POST":
        form = PaymentForm(request.POST, instance=payment, user=request.user)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.review_required, payment.review_reason = False, ""
            payment.save()
            flagged = flag_similar(payment)
            messages.success(request, _("✅ تم تحديث الدفعة.") + (_(" 🔎 وهي تشبه دفعة أخرى فتحتاج إلى مراجعة.") if flagged else ""))
            return redirect("payments:detail", pk=payment.pk)
        messages.error(request, _("❌ لم يتم الحفظ، راجع الحقول المظللة وصحّح الأخطاء."))
    else:
        form = PaymentForm(instance=payment, user=request.user)
    return render(
        request, "payments/form.html", {"form": form, "title": _("تعديل الدفعة #%(pk)s") % {"pk": payment.pk}, "is_edit": True, "payment": payment}
    )


@login_required
@require_POST
def payment_archive(request, pk):
    payment = _own_payment_or_404(request, pk)
    payment.is_archived = True
    payment.save(update_fields=["is_archived"])
    messages.success(request, _("📦 تمت أرشفة الدفعة #%(pk)s. لن تدخل في التقارير، ويمكنك استعادتها.") % {"pk": payment.pk})
    return redirect("payments:list")


@login_required
@require_POST
def payment_restore(request, pk):
    payment = _own_payment_or_404(request, pk)
    payment.is_archived = False
    payment.save(update_fields=["is_archived"])
    messages.success(request, _("♻️ تمت استعادة الدفعة #%(pk)s.") % {"pk": payment.pk})
    return redirect("payments:detail", pk=payment.pk)


@login_required
@require_POST
def payment_mark_reviewed(request, pk):
    payment = _own_payment_or_404(request, pk)
    payment.review_required, payment.review_reason = False, ""
    payment.save(update_fields=["review_required", "review_reason"])
    messages.success(request, _("✅ تمت مراجعة الدفعة وإزالة العلامة."))
    return redirect("payments:detail", pk=payment.pk)


@login_required
def payment_delete(request, pk):
    """Permanent delete is allowed only for archived payments, after confirmation."""
    payment = _own_payment_or_404(request, pk)
    if not payment.is_archived:
        messages.error(request, _("🚫 لا يمكن حذف دفعة نشطة؛ أرشفها أولًا ثم احذفها إن لزم."))
        return redirect("payments:detail", pk=payment.pk)
    if request.method == "POST":
        number = payment.pk
        payment.delete()
        messages.success(request, _("🗑️ تم حذف الدفعة #%(number)s نهائيًا.") % {"number": number})
        return redirect("payments:list")
    return render(request, "payments/confirm_delete.html", {"payment": payment})


@login_required
def payment_import(request):
    if request.method == "POST":
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            upload = form.cleaned_data["file"]
            if upload.size > MAX_BYTES:
                messages.error(request, _("❌ حجم الملف أكبر من الحد المسموح (1 ميغابايت)."))
                return render(request, "payments/import.html", {"form": form})
            created, flagged, errors = safe_import(upload.read(), request.user)
            if errors:
                messages.error(request, _("❌ لم يُحفظ شيء: الملف يحتوي على أخطاء. صحّحها وأعد المحاولة."))
                return render(
                    request,
                    "payments/import.html",
                    {
                        "form": ImportForm(),
                        "errors": errors[:MAX_ERRORS_SHOWN],
                        "more_errors": max(0, len(errors) - MAX_ERRORS_SHOWN),
                    },
                )
            text = _("✅ تم استيراد %(created)s دفعة بنجاح.") % {"created": created}
            if flagged:
                text += _(" 🔎 %(flagged)s منها تشبه دفعات أخرى وتحتاج إلى مراجعة.") % {"flagged": flagged}
            messages.success(request, text)
            return redirect("payments:list")
        messages.error(request, _("❌ اختر ملف JSON أولًا."))
    else:
        form = ImportForm()
    return render(request, "payments/import.html", {"form": form})
