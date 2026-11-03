
# استيراد timedelta للتعامل مع الفترات الزمنية، مثل إضافة 7 أيام إلى تاريخ اليوم
from datetime import timedelta

# استيراد الديكوريتر الذي يشترط تسجيل دخول المستخدم للوصول إلى الصفحة
from django.contrib.auth.decorators import login_required

# استيراد Count لحساب عدد السجلات، وQ لبناء شروط البحث في قاعدة البيانات
from django.db.models import Count, Q

# استيراد redirect لتحويل المستخدم إلى رابط آخر، وrender لعرض قالب HTML
from django.shortcuts import redirect, render

# استيراد timezone للتعامل مع التاريخ والوقت وفق إعدادات Django
from django.utils import timezone

# استيراد دالة للتحقق من أن رابط إعادة التوجيه مسموح وآمن
from django.utils.http import url_has_allowed_host_and_scheme

# استيراد الديكوريتر الذي يسمح بتنفيذ الدالة باستخدام طلب POST فقط
from django.views.decorators.http import require_POST

# استيراد نموذج الإشعارات للتعامل مع بيانات الإشعارات في قاعدة البيانات
from notifications.models import Notification

# استيراد نموذج المدفوعات لجلب عمليات الدفع الخاصة بالمستخدم
from payments.models import Payment

# استيراد نموذج الاشتراكات لجلب اشتراكات المستخدم
from subscriptions.models import Subscription

# استيراد دالة تحسب التكلفة الشهرية للاشتراكات حسب العملة
from subscriptions.services import monthly_cost_by_currency

# استيراد مدة السنة واسم ملف تعريف ارتباط الثيم وقائمة الثيمات المسموح بها
from .theme import ONE_YEAR, THEME_COOKIE, THEMES


# ==========================================
# لوحة التحكم (Dashboard)
# ==========================================

# يشترط تسجيل دخول المستخدم قبل عرض لوحة التحكم
@login_required
def dashboard(request):
    # دالة تعرض ملخصًا محدثًا اعتمادًا على البيانات الموجودة في قاعدة البيانات
    # الأرقام لا تُكتب يدويًا، بل تُحسب من بيانات الاشتراكات الفعلية

    # الحصول على تاريخ اليوم وفق المنطقة الزمنية المحلية للمشروع
    today = timezone.localdate()

    # جلب اشتراكات المستخدم الذي أرسل الطلب الحالي فقط
    subs = Subscription.objects.filter(user=request.user)

    # تصفية اشتراكات المستخدم للحصول على الاشتراكات النشطة فقط
    active = subs.filter(status=Subscription.Status.ACTIVE)

    # حساب عدة إحصائيات للاشتراكات في استعلام تجميعي واحد
    # aggregate() يعيد قاموسًا يحتوي على نتائج الحسابات المطلوبة
    stats = subs.aggregate(

        # حساب العدد الإجمالي لاشتراكات المستخدم
        total=Count("id"),

        # حساب عدد الاشتراكات النشطة فقط
        # filter=Q(...) يجعل العد مقتصرًا على الاشتراكات التي تحقق الشرط
        active=Count(
            "id",
            filter=Q(status=Subscription.Status.ACTIVE),
        ),

        # حساب الاشتراكات النشطة التي موعد تجديدها خلال الأيام السبعة القادمة
        renewing_soon=Count(
            "id",
            filter=Q(
                # يجب أن تكون حالة الاشتراك نشطة
                status=Subscription.Status.ACTIVE,

                # موعد التجديد يجب أن يكون اليوم أو بعده
                next_renewal_date__gte=today,

                # موعد التجديد يجب ألا يتجاوز سبعة أيام من اليوم
                next_renewal_date__lte=today + timedelta(days=7),
            ),
        ),

        # حساب الاشتراكات النشطة التي تجاوز موعد تجديدها تاريخ اليوم
        # هذه الاشتراكات تحتاج إلى مراجعة وفق منطق لوحة التحكم
        needs_review=Count(
            "id",
            filter=Q(
                status=Subscription.Status.ACTIVE,

                # __lt تعني أن تاريخ التجديد أقدم من تاريخ اليوم
                next_renewal_date__lt=today,
            ),
        ),
    )

    # تجهيز قائمة بالاشتراكات النشطة التي موعد تجديدها اليوم أو في المستقبل
    upcoming = (
        active.filter(
            # __gte تعني أن موعد التجديد أكبر من أو يساوي تاريخ اليوم
            next_renewal_date__gte=today
        )

        # جلب بيانات الفئة المرتبطة بكل اشتراك ضمن الاستعلام نفسه
        # يساعد ذلك على تقليل الاستعلامات الإضافية عند الوصول إلى category
        .select_related("category")

        # ترتيب الاشتراكات حسب أقرب موعد تجديد أولًا
        # وعند تساوي الموعد، يكون الترتيب حسب اسم الخدمة
        .order_by("next_renewal_date", "service_name")

        # إرجاع أول خمسة اشتراكات فقط
        # [:5] تحدد عدد النتائج وتساعد على تقليل البيانات المسترجعة
        [:5]
    )

    # جلب أحدث خمس عمليات دفع تخص المستخدم الحالي
    latest_payments = (
        Payment.objects.filter(
            # التأكد من أن عملية الدفع تخص المستخدم الحالي
            user=request.user,

            # استبعاد عمليات الدفع المؤرشفة
            is_archived=False,
        )

        # جلب بيانات الاشتراك المرتبط بكل عملية دفع
        # لتجنب استعلام منفصل عند الوصول إلى subscription
        .select_related("subscription")

        # ترتيب عمليات الدفع من الأحدث إلى الأقدم
        # علامة - قبل الحقل تعني الترتيب التنازلي
        # -pk يستخدم الرقم الأساسي كترتيب إضافي عند تساوي تاريخ الدفع
        .order_by("-payment_date", "-pk")

        # تحديد عدد النتائج بخمس عمليات دفع فقط
        [:5]
    )

    # جلب أحدث خمس إشعارات تخص المستخدم الحالي
    latest_notifications = (
        Notification.objects.filter(
            # عدم عرض إشعارات المستخدمين الآخرين
            user=request.user
        )

        # جلب بيانات الاشتراك المرتبط بالإشعار إن وجد
        .select_related("subscription")

        # ترتيب الإشعارات من الأحدث إلى الأقدم
        # عند تساوي تاريخ الإنشاء، يُستخدم المفتاح الأساسي للترتيب
        .order_by("-created_at", "-pk")

        # إرجاع أحدث خمسة إشعارات فقط
        [:5]
    )

    # عرض قالب لوحة التحكم وإرسال البيانات إليه
    return render(
        request,

        # مسار ملف HTML الذي سيعرض واجهة لوحة التحكم
        "core/dashboard.html",

        # قاموس البيانات الذي يمكن للقالب الوصول إلى قيمه
        {
            # الإحصائيات المحسوبة للاشتراكات
            "stats": stats,

            # التكلفة الشهرية التقديرية للاشتراكات النشطة حسب العملة
            "monthly_estimates": monthly_cost_by_currency(active),

            # قائمة الاشتراكات القادمة
            "upcoming": upcoming,

            # أحدث عمليات الدفع
            "latest_payments": latest_payments,

            # أحدث الإشعارات
            "latest_notifications": latest_notifications,
        },
    )


# ==========================================
# تغيير المظهر (Theme)
# ==========================================

# السماح بتنفيذ هذه الدالة عند إرسال طلب POST فقط
# هذا يعني أن الطلب يجب أن يرسل بيانات، بدل تغيير المظهر بطلب GET عادي
@require_POST
def set_theme(request):
    # دالة تحفظ المظهر الذي اختاره المستخدم في الجلسة وملف تعريف الارتباط
    # لا تحتاج هذه العملية إلى JavaScript وفق طريقة تنفيذها هنا

    # قراءة قيمة theme المرسلة في بيانات الطلب
    # POST.get() يعيد None إذا لم تكن القيمة موجودة
    chosen = request.POST.get("theme")

    # التحقق من أن المظهر المختار موجود ضمن قائمة الثيمات المسموح بها
    # إذا كانت القيمة غير صالحة، يتم اختيار المظهر الفاتح
    if chosen not in THEMES:
        chosen = "light"

    # قراءة الرابط الذي يُراد الرجوع إليه بعد تغيير المظهر
    # إذا لم يرسل المستخدم next، تكون الوجهة الصفحة الرئيسية
    target = request.POST.get("next", "/")

    # التحقق من أن الرابط آمن ومسموح بإعادة التوجيه إليه
    # allowed_hosts يحدد المضيف المسموح به، وهو مضيف الطلب الحالي
    # require_https يطلب استخدام HTTPS إذا كان الطلب الحالي آمنًا
    # يمنع هذا التحقق استخدام روابط إعادة توجيه خارجية غير مسموح بها
    if not url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):

        # إذا كان الرابط غير آمن أو غير مسموح به، استخدم الصفحة الرئيسية
        target = "/"

    # حفظ المظهر المختار داخل جلسة المستخدم
    # يمكن لأجزاء أخرى من المشروع قراءة هذه القيمة من request.session
    request.session["theme"] = chosen

    # إنشاء استجابة تعيد المستخدم إلى الرابط المحدد بعد التحقق منه
    response = redirect(target)

    # إنشاء ملف تعريف ارتباط يحتوي على المظهر المختار
    response.set_cookie(
        # اسم ملف تعريف الارتباط المحدد في إعدادات الثيم
        THEME_COOKIE,

        # القيمة التي سيتم تخزينها، مثل light أو dark إذا كانت ضمن THEMES
        chosen,

        # تحديد مدة صلاحية ملف تعريف الارتباط بالثواني
        # ONE_YEAR ثابت مستورد من ملف theme
        max_age=ONE_YEAR,

        # السماح بإرسال ملف تعريف الارتباط في التنقلات المناسبة
        # مع الحد من إرساله في بعض الطلبات الخارجية
        samesite="Lax",

        # منع JavaScript من قراءة ملف تعريف الارتباط مباشرة
        httponly=True,
    )

    # إرجاع الاستجابة إلى المتصفح
    # سيحفظ المتصفح ملف تعريف الارتباط وينتقل إلى الرابط المحدد
    return response
