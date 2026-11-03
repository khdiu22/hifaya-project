
# استيراد أدوات الترجمة حتى تظهر أسماء الحقول والرسائل باللغة المناسبة
from django.utils.translation import gettext_lazy as _

# استيراد Decimal للتعامل الدقيق مع الأرقام المالية
from decimal import Decimal

# استيراد إعدادات Django للوصول إلى نموذج المستخدم المعتمد في المشروع
from django.conf import settings

# استيراد ValidationError لإظهار أخطاء التحقق من صحة البيانات
from django.core.exceptions import ValidationError

# استيراد مدقق يتحقق من أن القيمة لا تقل عن حد معين
from django.core.validators import MinValueValidator

# استيراد أدوات إنشاء النماذج والحقول في Django
from django.db import models

# استيراد Q لبناء شروط يمكن استخدامها في استعلامات قاعدة البيانات
from django.db.models import Q

# استيراد العملات ونموذج الاشتراكات من تطبيق subscriptions
from subscriptions.models import Currency, Subscription


# إنشاء نموذج الدفعة Payment الذي يمثل عملية دفع في النظام
class Payment(models.Model):

    # تحديد الحالات الممكنة للدفعة
    # TextChoices تنشئ خيارات جاهزة للاستخدام في حقل الحالة
    class Status(models.TextChoices):
        PAID = "paid", _("مدفوعة")  # الدفعة تم دفعها
        PENDING = "pending", _("قيد الانتظار")  # الدفعة تنتظر إكمالها
        FAILED = "failed", _("فاشلة")  # عملية الدفع فشلت
        REFUNDED = "refunded", _("مستردة")  # تم استرداد المبلغ

    # ربط كل دفعة بالمستخدم الذي أنشأها
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # نموذج المستخدم المعتمد في إعدادات المشروع
        on_delete=models.CASCADE,  # حذف دفعات المستخدم عند حذف حسابه
        related_name="payments",  # يسمح باستخدام user.payments للوصول إلى دفعات المستخدم
        verbose_name=_("المستخدم"),  # الاسم الظاهر للحقل في الواجهات الإدارية
    )

    # ربط الدفعة باشتراك معين، وهذا الربط اختياري
    subscription = models.ForeignKey(
        Subscription,  # النموذج الذي ترتبط به الدفعة
        on_delete=models.RESTRICT,  # يمنع حذف الاشتراك إذا كانت هناك دفعات مرتبطة به
        null=True,  # يسمح بتخزين NULL في قاعدة البيانات إذا لم يوجد اشتراك
        blank=True,  # يسمح بترك الحقل فارغًا في النماذج
        related_name="payments",  # يسمح باستخدام subscription.payments للوصول إلى دفعات الاشتراك
        verbose_name=_("الاشتراك المرتبط"),  # الاسم الظاهر للحقل
    )

    # تخزين مبلغ الدفعة كرقم عشري مناسب للقيم المالية
    amount = models.DecimalField(
        _("المبلغ"),  # الاسم الظاهر للحقل
        max_digits=10,  # أقصى عدد إجمالي للأرقام، شاملًا الأرقام قبل الفاصلة وبعدها
        decimal_places=2,  # السماح بخانتين عشريتين
        validators=[
            # التحقق من أن المبلغ لا يقل عن صفر
            MinValueValidator(
                Decimal("0"),
                message=_("لا يمكن أن يكون المبلغ سالبًا."),
            )
        ],
    )

    # تخزين عملة الدفعة، مع تحديد العملات المسموح بها من Currency
    currency = models.CharField(
        _("العملة"),
        max_length=3,  # رمز العملة يتكون من ثلاثة أحرف مثل SAR أو USD
        choices=Currency.choices,  # الخيارات المسموح بها للعملة
        default=Currency.SAR,  # العملة الافتراضية هي الريال السعودي
    )

    # تخزين تاريخ الدفع دون الوقت
    payment_date = models.DateField(_("تاريخ الدفع"))

    # تخزين طريقة الدفع، مثل التحويل البنكي أو البطاقة
    # blank=True يعني أن الحقل يمكن تركه فارغًا في النموذج
    payment_method = models.CharField(
        _("طريقة الدفع"),
        max_length=50,  # أقصى طول للنص 50 حرفًا
        blank=True,
    )

    # تخزين الرقم المرجعي لعملية الدفع إن وجد
    reference = models.CharField(
        _("مرجع العملية"),
        max_length=100,  # أقصى طول للمرجع 100 حرف
        blank=True,
    )

    # تحديد حالة الدفعة، وتكون مدفوعة افتراضيًا
    status = models.CharField(
        _("الحالة"),
        max_length=10,  # أطول قيمة من الحالات المحددة لا تتجاوز 10 أحرف
        choices=Status.choices,  # استخدام الحالات المعرفة في Status
        default=Status.PAID,  # الحالة الافتراضية هي مدفوعة
    )

    # تحديد ما إذا كانت الدفعة تحتاج إلى مراجعة
    review_required = models.BooleanField(
        _("تحتاج إلى مراجعة"),
        default=False,  # لا تحتاج إلى مراجعة افتراضيًا
    )

    # تخزين سبب الحاجة إلى مراجعة الدفعة إن وجد
    review_reason = models.CharField(
        _("سبب المراجعة"),
        max_length=255,  # أقصى طول لسبب المراجعة 255 حرفًا
        blank=True,
    )

    # تخزين ملاحظات إضافية عن الدفعة
    # TextField مناسب للنصوص التي قد تكون أطول
    notes = models.TextField(_("ملاحظات"), blank=True)

    # تحديد ما إذا كانت الدفعة مؤرشفة
    is_archived = models.BooleanField(
        _("مؤرشفة"),
        default=False,  # الدفعة غير مؤرشفة افتراضيًا
    )

    # تسجيل تاريخ ووقت إنشاء الدفعة تلقائيًا عند إنشائها
    # auto_now_add لا يحدّث القيمة عند كل تعديل لاحق
    created_at = models.DateTimeField(
        _("تاريخ التسجيل"),
        auto_now_add=True,
    )

    # إعدادات إضافية للنموذج
    class Meta:
        # ترتيب الدفعات حسب التاريخ من الأحدث إلى الأقدم
        # وإذا تساوى التاريخ، تُرتب حسب رقم الدفعة تنازليًا
        ordering = ["-payment_date", "-id"]

        # الاسم المفرد للنموذج في واجهات Django
        verbose_name = _("دفعة")

        # الاسم الجمع للنموذج
        verbose_name_plural = _("المدفوعات")

        # إضافة قيود على مستوى قاعدة البيانات
        constraints = [
            models.CheckConstraint(
                # يمنع قاعدة البيانات من قبول مبلغ أقل من صفر
                condition=Q(amount__gte=0),

                # اسم فريد للقيد داخل قاعدة البيانات
                name="payment_amount_non_negative",

                # الرسالة التي توضح الخطأ عند انتهاك القيد
                violation_error_message=_("لا يمكن أن يكون المبلغ سالبًا."),
            )
        ]

    # التحقق من صحة البيانات والعلاقة بين الدفعة والمستخدم والاشتراك
    def clean(self):
        # تنفيذ عمليات التحقق الأصلية الموجودة في النموذج الأب
        super().clean()

        # إذا كانت الدفعة مرتبطة باشتراك وكان لها مستخدم
        if self.subscription_id and self.user_id:

            # التأكد من أن الاشتراك يعود إلى المستخدم نفسه
            if self.subscription.user_id != self.user_id:
                raise ValidationError(
                    {
                        "subscription": _(
                            "لا يمكنك ربط دفعة باشتراك لا يخصك."
                        )
                    }
                )

            # التأكد من أن عملة الدفعة تطابق عملة الاشتراك
            if self.currency and self.subscription.currency != self.currency:
                raise ValidationError(
                    {
                        "currency": _(
                            "عملة الدفعة يجب أن تطابق عملة الاشتراك (%(currency)s)."
                        )
                        % {"currency": self.subscription.currency}
                    }
                )

    # تحديد النص الذي يظهر عند طباعة كائن الدفعة
    def __str__(self):
        # مثال: #12 150.00 SAR
        return f"#{self.pk} {self.amount} {self.currency}"
