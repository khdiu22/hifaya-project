from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.utils import paginate

from .forms import NotificationFilterForm
from .models import Notification
from .services import send_due_reminders


@login_required
def notification_list(request):
    form = NotificationFilterForm(request.GET)
    if form.is_valid():
        data = form.cleaned_data
    else:
        data = {}
        messages.warning(request, _("⚠️ بعض عوامل التصفية غير صالحة وتم تجاهلها."))

    qs = Notification.objects.filter(user=request.user).select_related("subscription")
    if data.get("state") == "unread":
        qs = qs.filter(is_read=False)
    elif data.get("state") == "read":
        qs = qs.filter(is_read=True)
    if data.get("date_from"):
        qs = qs.filter(created_at__date__gte=data["date_from"])
    if data.get("date_to"):
        qs = qs.filter(created_at__date__lte=data["date_to"])
    qs = qs.order_by("-created_at", "-pk")

    return render(
        request,
        "notifications/list.html",
        {
            "form": form,
            "page_obj": paginate(request, qs),
            "has_filters": any(data.get(k) for k in ("state", "date_from", "date_to")),
            "has_any": Notification.objects.filter(user=request.user).exists(),
        },
    )


@login_required
@require_POST
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        messages.success(request, _("✅ تم تمييز الإشعار كمقروء."))
    target = request.POST.get("next", "")
    if not target or not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "notifications:list"
    return redirect(target)


@login_required
@require_POST
def notification_mark_all_read(request):
    updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if updated:
        messages.success(request, _("✅ تم تمييز %(updated)s إشعار كمقروء.") % {"updated": updated})
    else:
        messages.info(request, _("💡 لا توجد إشعارات غير مقروءة."))
    return redirect("notifications:list")


@login_required
@require_POST
def check_reminders(request):
    """User-triggered check (own subscriptions only). The daily automatic run
    needs the `send_reminders` command to be scheduled separately."""
    result = send_due_reminders(user=request.user)
    if result.created:
        messages.success(request, _("🔔 تم إنشاء %(created)s تذكير جديد.") % {"created": result.created})
    else:
        messages.info(request, _("💡 لا توجد تذكيرات جديدة مستحقة الآن."))
    return redirect("notifications:list")
