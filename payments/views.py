
# استيراد أدوات الترجمة لجعل الرسائل قابلة للعرض بلغات مختلفة
from django.utils.translation import gettext_lazy as _

# استيراد نظام الرسائل لإظهار إشعارات النجاح والتحذير والخطأ للمستخدم
from django.contrib import messages

# استيراد الديكور الذي يمنع المستخدم غير المسجل من الوصول إلى الصفحة
from django.contrib.auth.decorators import login_required

# استيراد أدوات جلب كائن من قاعدة البيانات، وإعادة التوجيه، وعرض القوالب
from django.shortcuts import get_object_or_404, redirect, render

# استيراد ديكور يسمح باستدعاء الدالة باستخدام POST فقط
from django.views.decorators.http import require_POST

# استيراد دالة تقسيم النتائج إلى صفحات
from core.utils import paginate

# استيراد النماذج المستخدمة في إنشاء الدفعات وتعديلها وتصفيتها واستيرادها
from .forms import ImportForm, PaymentFilterForm, PaymentForm

# استيراد حدود حجم ملف الاستيراد وعدد الأخطاء المعروضة ودالة الاستيراد الآمن
from .importer import MAX_ERRORS_SHOWN, MAX_BYTES, safe_import

# استيراد نموذج الدفعات من قاعدة البيانات
from .models import Payment

# استيراد دالة فحص الدفعات المتشابهة ووضع علامة المراجعة عليها
from .services import flag_similar


# تحديد ترتيب النتائج حسب الخيار الذي يختاره المستخدم
# المفتاح هو القيمة القادمة من نموذج التصفية
# والقيمة هي أسماء الحقول التي سيُرتب الاستعلام النتائج على أساسها
ORDERING_MAP = {
    "-date": ("-payment_date", "-id"),  # الأحدث أولًا، ثم رقم الدفعة تنازليًا
    "date": ("payment_date", "id"),  # الأقدم أولًا، ثم رقم الدفعة تصاعديًا
    "-amount": ("-amount", "-id"),  # المبالغ الأعلى أولًا
    "amount": ("amount", "id"),  # المبالغ الأقل أولًا
}


def _own_payment_or_404(request, pk):
    # جلب الدفعة المطلوبة مع الاشتراك المرتبط بها
    # select_related يقلل الاستعلامات عند الوصول إلى الاشتراك المرتبط
    # pk هو رقم الدفعة المطلوب
    # user=request.user يضمن جلب دفعة المستخدم الحالي فقط
    # إذا لم توجد الدفعة أو لم تكن ملكًا للمستخدم، تظهر صفحة 404
    return get_object_or_404(
        Payment.objects.select_related("subscription"),
        pk=pk,
        user=request.user,
    )


# لا يمكن الوصول إلى قائمة الدفعات إلا بعد تسجيل الدخول
@login_required
def payment_list(request):

    # إنشاء نموذج التصفية باستخدام البيانات الموجودة في عنوان URL
    # request.GET يحتوي على قيم مثل الحالة والتاريخ والترتيب
    form = PaymentFilterForm(request.GET, user=request.user)

    # التحقق من صحة قيم التصفية
    if form.is_valid():
        # استخدام القيم التي اجتازت التحقق
        data = form.cleaned_data
    else:
        # تجاهل قيم التصفية غير الصحيحة
        data = {}

        # إظهار تحذير للمستخدم
        messages.warning(
            request,
            _("⚠️ بعض عوامل التصفية غير صالحة وتم تجاهلها."),
        )

    # جلب دفعات المستخدم الحالي فقط
    # select_related يجلب بيانات الاشتراك المرتبط عند الحاجة
    qs = Payment.objects.filter(
        user=request.user
    ).select_related("subscription")

    # تحديد نوع الدفعات المطلوب عرضها
    # إذا لم يحدد المستخدم خيارًا، نعرض الدفعات النشطة
    show = data.get("show") or "active"

    # إذا كان الاختيار active، نستبعد الدفعات المؤرشفة
    if show == "active":
        qs = qs.filter(is_archived=False)

    # إذا كان الاختيار archived، نعرض الدفعات المؤرشفة فقط
    elif show == "archived":
        qs = qs.filter(is_archived=True)

    # تصفية الدفعات حسب الاشتراك المختار إذا تم تحديده
    if data.get("subscription"):
        qs = qs.filter(subscription=data["subscription"])

    # تصفية الدفعات حسب الحالة إذا تم تحديدها
    if data.get("status"):
        qs = qs.filter(status=data["status"])

    # عرض الدفعات التي يوافق تاريخها تاريخ البداية أو يأتي بعده
    if data.get("date_from"):
        qs = qs.filter(payment_date__gte=data["date_from"])

    # عرض الدفعات التي يوافق تاريخها تاريخ النهاية أو يسبقه
    if data.get("date_to"):
        qs = qs.filter(payment_date__lte=data["date_to"])

    # إذا اختار المستخدم عرض الدفعات التي تحتاج إلى مراجعة فقط
    if data.get("review"):
        qs = qs.filter(review_required=True)

    # تطبيق الترتيب المطلوب
    # إذا لم يحدد المستخدم ترتيبًا، نستخدم الأحدث أولًا
    # get يعيد الترتيب الافتراضي إذا كانت القيمة غير موجودة في القاموس
    qs = qs.order_by(
        *ORDERING_MAP.get(
            data.get("ordering") or "-date",
            ORDERING_MAP["-date"],
        )
    )

    # عرض صفحة قائمة الدفعات وإرسال البيانات اللازمة إلى القالب
    return render(
        request,
        "payments/list.html",
        {
            # نموذج التصفية لعرضه في الصفحة
            "form": form,

            # تقسيم النتائج إلى صفحات قبل عرضها
            "page_obj": paginate(request, qs),

            # تحديد ما إذا كانت هناك تصفية فعالة
            # يتم فحص الحقول المحددة، أو اختلاف نوع العرض عن النشط
            "has_filters": any(
                data.get(k)
                for k in (
                    "subscription",
                    "status",
                    "date_from",
                    "date_to",
                    "review",
                )
            ) or show != "active",

            # التحقق من وجود أي دفعة للمستخدم، بما فيها المؤرشفة
            "has_any": Payment.objects.filter(
                user=request.user
            ).exists(),

            # حساب عدد الدفعات غير المؤرشفة التي تحتاج إلى مراجعة
            "review_count": Payment.objects.filter(
                user=request.user,
                is_archived=False,
                review_required=True,
            ).count(),
        },
    )


# عرض تفاصيل دفعة معينة للمستخدم المسجل دخوله
@login_required
def payment_detail(request, pk):

    # التحقق من ملكية الدفعة ثم إرسالها إلى صفحة التفاصيل
    return render(
        request,
        "payments/detail.html",
        {"payment": _own_payment_or_404(request, pk)},
    )


# إنشاء دفعة جديدة
@login_required
def payment_create(request):

    # إذا أرسل المستخدم النموذج، نعالج بيانات POST
    if request.method == "POST":

        # ربط بيانات النموذج بالمستخدم الحالي
        form = PaymentForm(request.POST, user=request.user)

        # التأكد من صحة البيانات قبل الحفظ
        if form.is_valid():

            # حفظ الدفعة في قاعدة البيانات
            payment = form.save()

            # فحص الدفعة لمعرفة ما إذا كانت تشبه دفعة أخرى
            if flag_similar(payment):

                # إظهار تحذير إذا عُثر على دفعات مشابهة
                messages.warning(
                    request,
                    _(
                        "🔎 تم حفظ الدفعة، وهي تشبه دفعة أخرى "
                        "فوُضعت علامة «تحتاج إلى مراجعة»."
                    ),
                )
            else:
                # إظهار رسالة نجاح إذا لم توجد دفعات مشابهة
                messages.success(
                    request,
                    _("✅ تم تسجيل الدفعة بنجاح!"),
                )

            # الانتقال إلى صفحة تفاصيل الدفعة بعد الحفظ
            return redirect("payments:detail", pk=payment.pk)

        # إذا كانت البيانات غير صحيحة، نعرض رسالة خطأ
        messages.error(
            request,
            _("❌ لم يتم الحفظ، راجع الحقول المظللة وصحّح الأخطاء."),
        )

    # إذا كانت الصفحة تُفتح لأول مرة ولم يتم إرسال النموذج
    else:
        # تجهيز قيم افتراضية للنموذج
        initial = {}

        # محاولة قراءة رقم الاشتراك من عنوان URL
        subscription_id = request.GET.get("subscription")

        # التأكد من أن رقم الاشتراك يحتوي على أرقام فقط
        if subscription_id and subscription_id.isdigit():

            # استيراد نموذج Subscription داخل هذا الجزء عند الحاجة إليه
            from subscriptions.models import Subscription

            # البحث عن الاشتراك بشرط أن يكون تابعًا للمستخدم الحالي
            # first يعيد أول كائن مطابق أو None إذا لم يوجد
            sub = Subscription.objects.filter(
                pk=int(subscription_id),
                user=request.user,
            ).first()

            # إذا وجد الاشتراك، نملأ بعض الحقول تلقائيًا
            if sub:
                initial = {
                    "subscription": sub,
                    "amount": sub.amount,
                    "currency": sub.currency,
                }

        # إنشاء نموذج فارغ مع القيم الافتراضية إن وجدت
        form = PaymentForm(
            user=request.user,
            initial=initial,
        )

    # عرض صفحة إنشاء الدفعة
    return render(
        request,
        "payments/form.html",
        {
            "form": form,
            "title": _("تسجيل دفعة"),
            "is_edit": False,  # توضيح أن الصفحة مخصصة لإنشاء دفعة جديدة
        },
    )


# تعديل دفعة موجودة
@login_required
def payment_update(request, pk):

    # جلب الدفعة والتأكد من أنها تخص المستخدم الحالي
    payment = _own_payment_or_404(request, pk)

    # منع تعديل الدفعة إذا كانت مؤرشفة
    if payment.is_archived:
        messages.info(
            request,
            _("💡 هذه الدفعة مؤرشفة؛ استعدها أولًا إذا أردت تعديلها."),
        )

        # إعادة المستخدم إلى صفحة تفاصيل الدفعة
        return redirect("payments:detail", pk=payment.pk)

    # إذا أرسل المستخدم بيانات التعديل
    if request.method == "POST":

        # إنشاء نموذج مرتبط بالدفعة الحالية وبالبيانات الجديدة
        form = PaymentForm(
            request.POST,
            instance=payment,
            user=request.user,
        )

        # التحقق من صحة بيانات التعديل
        if form.is_valid():

            # تجهيز التعديلات دون حفظها مباشرة
            payment = form.save(commit=False)

            # إزالة علامة المراجعة القديمة وسببها
            # لأن بيانات الدفعة تغيرت وسيعاد فحص التشابه
            payment.review_required, payment.review_reason = False, ""

            # حفظ التعديلات في قاعدة البيانات
            payment.save()

            # إعادة فحص الدفعة بعد تحديثها
            flagged = flag_similar(payment)

            # إظهار رسالة نجاح، وإضافة تنبيه إذا كانت الدفعة مشابهة لغيرها
            messages.success(
                request,
                _("✅ تم تحديث الدفعة.")
                + (
                    _(" 🔎 وهي تشبه دفعة أخرى فتحتاج إلى مراجعة.")
                    if flagged
                    else ""
                ),
            )

            # الانتقال إلى صفحة تفاصيل الدفعة بعد التحديث
            return redirect("payments:detail", pk=payment.pk)

        # إظهار رسالة خطأ إذا كانت بيانات التعديل غير صحيحة
        messages.error(
            request,
            _("❌ لم يتم الحفظ، راجع الحقول المظللة وصحّح الأخطاء."),
        )

    # إذا لم يُرسل المستخدم النموذج، نعرض بيانات الدفعة الحالية
    else:
        form = PaymentForm(
            instance=payment,
            user=request.user,
        )

    # عرض نموذج التعديل
    return render(
        request,
        "payments/form.html",
        {
            "form": form,
            "title": _("تعديل الدفعة #%(pk)s") % {"pk": payment.pk},
            "is_edit": True,  # توضيح أن الصفحة مخصصة للتعديل
            "payment": payment,
        },
    )


# أرشفة دفعة موجودة
@login_required
@require_POST  # لا يسمح بتنفيذ الأرشفة باستخدام GET
def payment_archive(request, pk):

    # جلب الدفعة الخاصة بالمستخدم الحالي
    payment = _own_payment_or_404(request, pk)

    # تغيير حالة الأرشفة إلى True
    payment.is_archived = True

    # حفظ حقل الأرشفة فقط بدل تحديث جميع حقول النموذج
    payment.save(update_fields=["is_archived"])

    # إبلاغ المستخدم بنجاح الأرشفة
    messages.success(
        request,
        _(
            "📦 تمت أرشفة الدفعة #%(pk)s. "
            "لن تدخل في التقارير، ويمكنك استعادتها."
        ) % {"pk": payment.pk},
    )

    # العودة إلى قائمة الدفعات
    return redirect("payments:list")


# استعادة دفعة مؤرشفة
@login_required
@require_POST  # لا يسمح بتنفيذ الاستعادة باستخدام GET
def payment_restore(request, pk):

    # جلب الدفعة والتأكد من ملكيتها للمستخدم
    payment = _own_payment_or_404(request, pk)

    # إلغاء الأرشفة
    payment.is_archived = False

    # حفظ حقل الأرشفة فقط
    payment.save(update_fields=["is_archived"])

    # إظهار رسالة نجاح
    messages.success(
        request,
        _("♻️ تمت استعادة الدفعة #%(pk)s.") % {"pk": payment.pk},
    )

    # الانتقال إلى صفحة تفاصيل الدفعة
    return redirect("payments:detail", pk=payment.pk)


# إزالة علامة المراجعة بعد مراجعة الدفعة
@login_required
@require_POST  # لا يسمح بتنفيذ العملية باستخدام GET
def payment_mark_reviewed(request, pk):

    # جلب الدفعة والتأكد من ملكيتها للمستخدم
    payment = _own_payment_or_404(request, pk)

    # إزالة علامة الحاجة إلى المراجعة ومسح سببها
    payment.review_required, payment.review_reason = False, ""

    # حفظ الحقلين اللذين تغيرا فقط
    payment.save(
        update_fields=["review_required", "review_reason"]
    )

    # إبلاغ المستخدم بنجاح إزالة العلامة
    messages.success(
        request,
        _("✅ تمت مراجعة الدفعة وإزالة العلامة."),
    )

    # العودة إلى صفحة تفاصيل الدفعة
    return redirect("payments:detail", pk=payment.pk)


# حذف دفعة نهائيًا، بشرط أن تكون مؤرشفة وبعد التأكيد
@login_required
def payment_delete(request, pk):

    # جلب الدفعة والتأكد من ملكيتها للمستخدم
    payment = _own_payment_or_404(request, pk)

    # منع حذف الدفعات النشطة
    if not payment.is_archived:
        messages.error(
            request,
            _("🚫 لا يمكن حذف دفعة نشطة؛ أرشفها أولًا ثم احذفها إن لزم."),
        )

        # العودة إلى صفحة تفاصيل الدفعة
        return redirect("payments:detail", pk=payment.pk)

    # تنفيذ الحذف فقط إذا أرسل المستخدم طلب POST للتأكيد
    if request.method == "POST":

        # حفظ رقم الدفعة قبل حذفها لاستخدامه في رسالة النجاح
        number = payment.pk

        # حذف الدفعة نهائيًا من قاعدة البيانات
        payment.delete()

        # إظهار رسالة تؤكد نجاح الحذف
        messages.success(
            request,
            _("🗑️ تم حذف الدفعة #%(number)s نهائيًا.")
            % {"number": number},
        )

        # العودة إلى قائمة الدفعات
        return redirect("payments:list")

    # إذا كان الطلب GET، نعرض صفحة تأكيد الحذف دون تنفيذ الحذف
    return render(
        request,
        "payments/confirm_delete.html",
        {"payment": payment},
    )


# استيراد دفعات متعددة من ملف JSON
@login_required
def payment_import(request):

    # إذا أرسل المستخدم نموذج الاستيراد
    if request.method == "POST":

        # ربط بيانات النموذج والملف المرفوع
        form = ImportForm(request.POST, request.FILES)

        # التحقق من صحة النموذج ووجود الملف
        if form.is_valid():

            # استخراج الملف بعد اجتياز التحقق
            upload = form.cleaned_data["file"]

            # فحص حجم الملف قبل قراءة محتواه
            if upload.size > MAX_BYTES:
                messages.error(
                    request,
                    _("❌ حجم الملف أكبر من الحد المسموح (1 ميغابايت)."),
                )

                # إعادة عرض الصفحة مع النموذج
                return render(
                    request,
                    "payments/import.html",
                    {"form": form},
                )

            # قراءة محتوى الملف وتمريره إلى دالة الاستيراد الآمن
            # request.user يضمن أن التحقق يتم بالنسبة للمستخدم الحالي
            created, flagged, errors = safe_import(
                upload.read(),
                request.user,
            )

            # إذا وُجدت أخطاء، نعرضها ولا نتابع كأن الاستيراد نجح
            if errors:
                messages.error(
                    request,
                    _(
                        "❌ لم يُحفظ شيء: الملف يحتوي على أخطاء. "
                        "صحّحها وأعد المحاولة."
                    ),
                )

                # إعادة عرض صفحة الاستيراد مع قائمة الأخطاء
                return render(
                    request,
                    "payments/import.html",
                    {
                        # إنشاء نموذج جديد لمحاولة رفع ملف آخر
                        "form": ImportForm(),

                        # عرض أول عدد محدد من الأخطاء فقط
                        "errors": errors[:MAX_ERRORS_SHOWN],

                        # حساب عدد الأخطاء التي لم تُعرض
                        "more_errors": max(
                            0,
                            len(errors) - MAX_ERRORS_SHOWN,
                        ),
                    },
                )

            # إنشاء رسالة نجاح تحتوي على عدد الدفعات المستوردة
            text = _("✅ تم استيراد %(created)s دفعة بنجاح.") % {
                "created": created
            }

            # إضافة عدد الدفعات التي تحتاج إلى مراجعة، إذا وُجدت
            if flagged:
                text += _(
                    " 🔎 %(flagged)s منها تشبه دفعات أخرى "
                    "وتحتاج إلى مراجعة."
                ) % {"flagged": flagged}

            # عرض رسالة نجاح الاستيراد
            messages.success(request, text)

            # العودة إلى قائمة الدفعات
            return redirect("payments:list")

        # إذا لم يجتز النموذج التحقق، نعرض رسالة خطأ
        messages.error(
            request,
            _("❌ اختر ملف JSON أولًا."),
        )

    # إذا كانت الصفحة تُفتح لأول مرة، نجهز نموذجًا فارغًا
    else:
        form = ImportForm()

    # عرض صفحة استيراد الدفعات
    return render(
        request,
        "payments/import.html",
        {"form": form},
    )
