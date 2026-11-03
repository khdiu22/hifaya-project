
"""
Section 5: reports.
كل الأرقام في التقارير يتم حسابها من قاعدة البيانات باستخدام Django ORM
مثل aggregate() و annotate()، ولا يتم جمع مبالغ بعملات مختلفة مع بعضها.
"""

# نستخدم هذا الديكوريتر للتأكد أن المستخدم مسجل دخوله قبل عرض التقارير
from django.contrib.auth.decorators import login_required

# Count: لحساب عدد السجلات
# Q: لإنشاء شروط استعلام يمكن دمجها باستخدام & و |
# Sum: لجمع القيم الرقمية الموجودة في قاعدة البيانات
from django.db.models import Count, Q, Sum

# render: لعرض صفحة HTML وإرسال البيانات إليها
from django.shortcuts import render

# timezone: للتعامل مع التاريخ والوقت حسب إعدادات Django
from django.utils import timezone

# استيراد نموذج المدفوعات
from payments.models import Payment

# استيراد التصنيفات والعملات والاشتراكات
from subscriptions.models import Category, Currency, Subscription

# دالة تحسب التكلفة الشهرية التقديرية للاشتراكات حسب كل عملة
from subscriptions.services import monthly_cost_by_currency

# استيراد نموذج الفلترة الخاص بصفحة التقارير
from .forms import ReportFilterForm


# لا يمكن فتح التقارير إلا بعد تسجيل الدخول
@login_required
def report(request):

    # إنشاء نموذج الفلترة باستخدام القيم الموجودة في الرابط GET
    # وتمرير المستخدم الحالي حتى تُحدد خيارات الفلترة المناسبة له
    form = ReportFilterForm(request.GET, user=request.user)

    # التحقق من صحة البيانات المدخلة في نموذج الفلترة
    # إذا كانت صحيحة، نأخذ القيم المنظفة من cleaned_data
    # وإذا كانت غير صحيحة، نستخدم قاموسًا فارغًا
    data = form.cleaned_data if form.is_valid() else {}

    # الحصول على تاريخ اليوم حسب المنطقة الزمنية المحددة في Django
    today = timezone.localdate()

    # استخراج تاريخ البداية والنهاية من بيانات الفلترة
    # إذا لم يُدخل المستخدم أحد التاريخين، ستكون قيمته None
    date_from, date_to = data.get("date_from"), data.get("date_to")

    # --------------------------------------------------
    # تجهيز بيانات المستخدم الحالي فقط
    # --------------------------------------------------

    # جلب اشتراكات المستخدم المسجل دخوله
    subs = Subscription.objects.filter(user=request.user)

    # جلب مدفوعات المستخدم الحالي التي لم تتم أرشفتها
    payments = Payment.objects.filter(
        user=request.user,
        is_archived=False,
    )

    # إذا اختار المستخدم حالة اشتراك معينة، نفلتر الاشتراكات والمدفوعات
    # حسب حالة الاشتراك المرتبط بكل دفعة
    if data.get("status"):
        subs = subs.filter(status=data["status"])
        payments = payments.filter(subscription__status=data["status"])

    # إذا اختار المستخدم تصنيفًا معينًا، نفلتر الاشتراكات والمدفوعات
    # حسب التصنيف المرتبط بالاشتراك
    if data.get("category"):
        subs = subs.filter(category=data["category"])
        payments = payments.filter(subscription__category=data["category"])

    # إذا اختار اشتراكًا محددًا، نعرض بيانات هذا الاشتراك فقط
    # ونربط المدفوعات بالاشتراك المحدد
    if data.get("subscription"):
        subs = subs.filter(pk=data["subscription"].pk)
        payments = payments.filter(subscription=data["subscription"])

    # إذا حدد المستخدم تاريخ بداية، نستبعد المدفوعات الأقدم منه
    # gte تعني Greater Than or Equal To، أي أكبر من أو يساوي
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)

    # إذا حدد المستخدم تاريخ نهاية، نستبعد المدفوعات الأحدث منه
    # lte تعني Less Than or Equal To، أي أقل من أو يساوي
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)

    # --------------------------------------------------
    # 1. حساب عدد الاشتراكات حسب الحالة
    # --------------------------------------------------

    # تحويل اختيارات الحالات إلى قاموس يحتوي على القيمة والاسم المعروض
    # مثال: قد تكون القيمة ACTIVE والاسم المعروض Active
    status_labels = dict(Subscription.Status.choices)

    # تجهيز قائمة تحتوي على اسم كل حالة وعدد الاشتراكات التابعة لها
    status_stats = [
        {
            # إظهار اسم الحالة المقروء بدل القيمة المخزنة
            # وإذا لم نجد الاسم في القاموس، نستخدم القيمة نفسها
            "label": status_labels.get(row["status"], row["status"]),

            # عدد الاشتراكات في هذه الحالة
            "total": row["total"],
        }
        for row in (
            subs.order_by()  # إزالة أي ترتيب سابق غير مطلوب للاستعلام
            .values("status")  # تجميع النتائج حسب حقل الحالة
            .annotate(total=Count("id"))  # حساب عدد الاشتراكات في كل حالة
            .order_by("status")  # ترتيب النتائج حسب قيمة الحالة
        )
    ]

    # --------------------------------------------------
    # 2. حساب عدد الاشتراكات في كل تصنيف
    # --------------------------------------------------

    # جلب التصنيفات وإضافة عدد الاشتراكات المرتبطة بكل تصنيف
    category_stats = (
        Category.objects.annotate(
            total=Count(
                "subscriptions",

                # حساب الاشتراكات الموجودة ضمن قائمة subs فقط
                # Q ينشئ شرطًا يمكن استخدامه داخل الاستعلام
                filter=Q(subscriptions__in=subs.values("pk")),
            )
        )
        # إظهار التصنيفات التي لديها اشتراك واحد على الأقل
        .filter(total__gt=0)

        # ترتيب التصنيفات من الأكثر اشتراكات إلى الأقل
        # وإذا تساوى العدد، يكون الترتيب حسب الاسم
        .order_by("-total", "name")
    )

    # --------------------------------------------------
    # 3. حساب المدفوعات المدفوعة حسب العملة
    # --------------------------------------------------

    # إنشاء شرط يحدد المدفوعات التي حالتها PAID فقط
    paid = Q(status=Payment.Status.PAID)

    # تجهيز عمليات الحساب التي ستُنفذ في استعلام واحد
    aggregates = {
        # حساب العدد الإجمالي للمدفوعات الموجودة في الاستعلام
        "payments_count": Count("id"),

        # حساب عدد المدفوعات التي حالتها PAID فقط
        "paid_count": Count("id", filter=paid),
    }

    # المرور على جميع العملات المعرفة في نموذج Currency
    for code in Currency.values:

        # حساب مجموع المبالغ المدفوعة لكل عملة على حدة
        # لا نجمع مبالغ العملات المختلفة مع بعضها
        aggregates[f"total_{code}"] = Sum(
            "amount",
            filter=paid & Q(currency=code),
        )

        # حساب عدد المدفوعات المدفوعة بهذه العملة
        aggregates[f"count_{code}"] = Count(
            "id",
            filter=paid & Q(currency=code),
        )

    # تنفيذ عمليات التجميع على قاعدة البيانات وإرجاع النتائج في قاموس
    totals = payments.aggregate(**aggregates)

    # تجهيز قائمة تحتوي على إجمالي المدفوعات لكل عملة
    currency_totals = [
        {
            # رمز العملة، مثل SAR أو USD
            "currency": code,

            # الاسم المعروض للعملة حسب الاختيارات المعرفة في Currency
            "label": Currency(code).label,

            # مجموع المبالغ المدفوعة بهذه العملة
            "total": totals[f"total_{code}"],

            # عدد المدفوعات المدفوعة بهذه العملة
            "count": totals[f"count_{code}"],
        }
        # المرور على العملات المعرفة في النموذج
        for code in Currency.values

        # عدم إظهار العملة إذا لم توجد لها أي مدفوعات مدفوعة
        if totals[f"count_{code}"]
    ]

    # --------------------------------------------------
    # 4. حساب إجمالي المدفوعات المدفوعة لكل اشتراك
    # --------------------------------------------------

    # إنشاء شرط يحدد المدفوعات المرتبطة بالاشتراكات
    # بشرط ألا تكون المدفوعات مؤرشفة وأن تكون حالتها PAID
    pay_filter = Q(
        payments__is_archived=False,
        payments__status=Payment.Status.PAID,
    )

    # إذا حُدد تاريخ بداية، نضيف شرطًا لاستبعاد المدفوعات الأقدم
    if date_from:
        pay_filter &= Q(payments__payment_date__gte=date_from)

    # إذا حُدد تاريخ نهاية، نضيف شرطًا لاستبعاد المدفوعات الأحدث
    if date_to:
        pay_filter &= Q(payments__payment_date__lte=date_to)

    # إضافة معلومات محسوبة لكل اشتراك
    per_subscription = (
        subs.annotate(
            # حساب مجموع المبالغ المدفوعة المرتبطة بكل اشتراك
            # مع تطبيق شروط pay_filter
            total_paid=Sum("payments__amount", filter=pay_filter),

            # حساب عدد المدفوعات المطابقة للشروط لكل اشتراك
            payments_n=Count("payments", filter=pay_filter),
        )
        # عرض الاشتراكات التي لديها دفعة مطابقة واحدة على الأقل
        .filter(payments_n__gt=0)

        # ترتيب الاشتراكات من الأعلى في إجمالي المدفوعات إلى الأقل
        # ثم حسب اسم الخدمة عند تساوي الإجمالي
        .order_by("-total_paid", "service_name")
    )

    # --------------------------------------------------
    # 5. حساب عدد الاشتراكات التي موعد تجديدها في الفترة المحددة
    # --------------------------------------------------

    # نستخدم None افتراضيًا حتى نعرف أنه لم يتم حساب العدد بعد
    renewals_count = None

    # لا نحسب عدد التجديدات إلا إذا اختار المستخدم تاريخ بداية
    # أو تاريخ نهاية للفترة
    if date_from or date_to:

        # نبدأ بشرط أن تكون حالة الاشتراك ACTIVE
        renew_q = Q(status=Subscription.Status.ACTIVE)

        # إذا حدد المستخدم تاريخ بداية، نضيف شرط موعد التجديد
        # ليكون في هذا التاريخ أو بعده
        if date_from:
            renew_q &= Q(next_renewal_date__gte=date_from)

        # إذا حدد المستخدم تاريخ نهاية، نضيف شرط موعد التجديد
        # ليكون في هذا التاريخ أو قبله
        if date_to:
            renew_q &= Q(next_renewal_date__lte=date_to)

        # حساب عدد الاشتراكات التي تطابق شروط التجديد
        renewals_count = subs.aggregate(
            n=Count("id", filter=renew_q)
        )["n"]

    # --------------------------------------------------
    # 6. حساب التكلفة الشهرية التقديرية للاشتراكات النشطة
    # --------------------------------------------------

    # إرسال الاشتراكات النشطة فقط إلى دالة حساب التكلفة الشهرية
    # وتُحسب النتائج منفصلة حسب العملة
    monthly_estimates = monthly_cost_by_currency(
        subs.filter(status=Subscription.Status.ACTIVE)
    )

    # --------------------------------------------------
    # 7. تحديد الاشتراكات والمدفوعات التي تحتاج إلى مراجعة
    # --------------------------------------------------

    # جلب الاشتراكات النشطة التي تجاوز موعد تجديدها تاريخ اليوم
    review_subs = (
        subs.filter(
            status=Subscription.Status.ACTIVE,
            next_renewal_date__lt=today,
        )

        # جلب التصنيف المرتبط بكل اشتراك في الاستعلام نفسه
        # لتقليل الاستعلامات الإضافية عند الوصول إلى category في القالب
        .select_related("category")

        # ترتيب الاشتراكات حسب أقرب موعد تجديد سابق
        .order_by("next_renewal_date")
    )

    # حساب عدد المدفوعات التي تم وضع علامة أنها تحتاج إلى مراجعة
    review_payments_count = payments.aggregate(
        n=Count("id", filter=Q(review_required=True))
    )["n"]

    # التحقق مما إذا كان لدى المستخدم أي اشتراكات أو مدفوعات
    # حتى لو لم تظهر نتائج بسبب الفلاتر الحالية
    has_data = (
        Subscription.objects.filter(user=request.user).exists()
        or Payment.objects.filter(user=request.user).exists()
    )

    # --------------------------------------------------
    # إرسال البيانات إلى صفحة التقارير وعرضها للمستخدم
    # --------------------------------------------------

    return render(
        request,

        # مسار قالب HTML الخاص بالتقارير
        "reports/report.html",

        # قاموس البيانات التي ستستخدمها صفحة HTML
        {
            # نموذج الفلترة لعرضه في الصفحة
            "form": form,

            # هل لدى المستخدم بيانات محفوظة؟
            "has_data": has_data,

            # إحصائيات الاشتراكات حسب الحالة
            "status_stats": status_stats,

            # إحصائيات الاشتراكات حسب التصنيف
            "category_stats": category_stats,

            # إجمالي المدفوعات حسب العملة
            "currency_totals": currency_totals,

            # العدد الإجمالي للمدفوعات المطابقة للفلاتر
            "payments_count": totals["payments_count"],

            # إجمالي المدفوعات لكل اشتراك
            "per_subscription": per_subscription,

            # عدد الاشتراكات التي موعد تجديدها في الفترة المحددة
            "renewals_count": renewals_count,

            # التكلفة الشهرية التقديرية حسب العملة
            "monthly_estimates": monthly_estimates,

            # الاشتراكات النشطة التي تجاوزت موعد تجديدها
            "review_subs": review_subs,

            # عدد المدفوعات التي تحتاج إلى مراجعة
            "review_payments_count": review_payments_count,

            # True إذا اختار المستخدم تاريخ بداية أو نهاية
            # وFalse إذا لم يحدد أي تاريخ
            "period_chosen": bool(date_from or date_to),
        },
    )
