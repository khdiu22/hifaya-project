
# استيراد timedelta للتعامل مع الفترات الزمنية وإضافة أو طرح عدد من الأيام
from datetime import timedelta

# استيراد gettext لترجمة النص حسب اللغة النشطة وقت استدعاء الدالة
from django.utils.translation import gettext as _

# استيراد نموذج Payment للتعامل مع الدفعات في قاعدة البيانات
from .models import Payment


# تحديد عدد الأيام التي نعتبرها نطاقًا زمنيًا للبحث عن دفعات متشابهة
SIMILARITY_DAYS = 3


def review_reason():
    # إنشاء رسالة توضح سبب وضع علامة المراجعة على الدفعة
    # gettext تُترجم النص باستخدام اللغة النشطة وقت استدعاء الدالة
    # نضع عدد الأيام داخل الرسالة بدلًا من كتابة الرقم مباشرة
    return _(
        "مدفوعات متشابهة: نفس الاشتراك والمبلغ والعملة وتاريخ متقارب "
        "(خلال %(days)s أيام). قد تكون مقصودة، راجعها بنفسك."
    ) % {"days": SIMILARITY_DAYS}


def find_similar(payment):
    # البحث عن دفعات أخرى للمستخدم نفسه تشترك مع الدفعة الحالية في:
    # الاشتراك، والمبلغ، والعملة، وتقارب تاريخ الدفع.
    # التشابه لا يعني بالضرورة أن الدفعة مكررة أو احتيالية.

    # إذا لم تكن الدفعة مرتبطة باشتراك، فلا نبحث عن دفعات مشابهة
    if not payment.subscription_id:
        return Payment.objects.none()

    # تحويل عدد الأيام المحدد إلى فترة زمنية
    window = timedelta(days=SIMILARITY_DAYS)

    # البحث في قاعدة البيانات عن الدفعات التي تطابق الشروط
    return Payment.objects.filter(
        # يجب أن تكون الدفعات تابعة للمستخدم نفسه
        user_id=payment.user_id,

        # يجب أن تكون مرتبطة بالاشتراك نفسه
        subscription_id=payment.subscription_id,

        # يجب أن يكون مبلغ الدفعة مطابقًا للمبلغ الحالي
        amount=payment.amount,

        # يجب أن تكون العملة مطابقة
        currency=payment.currency,

        # استبعاد الدفعات المؤرشفة من نتائج البحث
        is_archived=False,

        # البحث عن الدفعات التي يقع تاريخها ضمن ثلاثة أيام
        # قبل تاريخ الدفعة الحالية أو ثلاثة أيام بعدها
        payment_date__range=(
            payment.payment_date - window,
            payment.payment_date + window,
        ),

    # استبعاد الدفعة الحالية من النتائج حتى لا تعتبر مشابهة لنفسها
    ).exclude(pk=payment.pk)


def flag_similar(payment):
    # فحص الدفعات المشابهة للدفعة الحالية ووضع علامة مراجعة عليها
    # لا تحذف هذه الدالة أي دفعة

    # استخراج أرقام الدفعات المشابهة وتحويلها إلى قائمة
    ids = list(find_similar(payment).values_list("pk", flat=True))

    # إذا لم توجد أي دفعات مشابهة، نرجع False
    if not ids:
        return False

    # تجهيز رسالة توضح سبب الحاجة إلى المراجعة
    reason = review_reason()

    # تحديث الدفعات المشابهة والدفعة الحالية معًا
    Payment.objects.filter(
        # تحديد أرقام الدفعات المشابهة وإضافة رقم الدفعة الحالية
        pk__in=ids + [payment.pk]
    ).update(
        # وضع علامة تفيد بأن الدفعة تحتاج إلى مراجعة
        review_required=True,

        # تخزين سبب المراجعة في قاعدة البيانات
        review_reason=reason,
    )

    # تحديث خصائص الكائن الحالي في الذاكرة أيضًا
    # لأن update() لا يحدّث كائن payment الموجود أمامنا تلقائيًا
    payment.review_required = True
    payment.review_reason = reason

    # إرجاع True للدلالة على العثور على دفعات مشابهة ووضع علامة مراجعة
    return True
