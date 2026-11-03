
# استيراد gettext_lazy لترجمة النصوص حسب اللغة النشطة في Django
# نستخدم الرمز _ كاختصار للدالة
from django.utils.translation import gettext_lazy as _

# استيراد Decimal للتعامل مع المبالغ المالية بدقة
from decimal import Decimal

# استيراد إعدادات Django، ومنها نموذج المستخدم المعتمد في المشروع
from django.conf import settings

# استيراد أدوات التحقق من القيم:
# MaxValueValidator يحدد القيمة القصوى
# MinValueValidator يحدد القيمة الدنيا
from django.core.validators import MaxValueValidator, MinValueValidator

# استيراد models لإنشاء نماذج قاعدة البيانات وحقولها
from django.db import models

# استيراد F لاستخدام قيمة حقل آخر في الاستعلامات والقيود
# واستيراد Q لبناء شروط يمكن دمجها باستخدام OR و AND و NOT
from django.db.models import F, Q

# استيراد Lower لتحويل النص إلى أحرف صغيرة داخل استعلامات قاعدة البيانات
from django.db.models.functions import Lower

# استيراد timezone للتعامل مع التاريخ والوقت وفق إعدادات Django
from django.utils import timezone

# استيراد gettext لترجمة النصوص وقت استخدامها
from django.utils.translation import gettext


# تعريف قائمة العملات المتاحة في المشروع
# TextChoices تنظّم الخيارات وتحدد القيمة المخزنة والنص المعروض للمستخدم
class Currency(models.TextChoices):

    # تخزين رمز SAR وعرض اسم الريال السعودي
    SAR = "SAR", _("ريال سعودي (SAR)")

    # تخزين رمز USD وعرض اسم الدولار الأمريكي
    USD = "USD", _("دولار أمريكي (USD)")

    # تخزين رمز EUR وعرض اسم اليورو
    EUR = "EUR", _("يورو (EUR)")

    # تخزين رمز GBP وعرض اسم الجنيه الإسترليني
    GBP = "GBP", _("جنيه إسترليني (GBP)")

    # تخزين رمز AED وعرض اسم الدرهم الإماراتي
    AED = "AED", _("درهم إماراتي (AED)")


# إنشاء نموذج التصنيفات الذي يخزن تصنيفات الاشتراكات
class Category(models.Model):

    # اسم التصنيف، بحد أقصى 80 حرفًا
    name = models.CharField(
        _("اسم التصنيف"),
        max_length=80
    )

    # وصف التصنيف، بحد أقصى 200 حرف
    # blank=True يسمح بترك الوصف فارغًا في النماذج
    description = models.CharField(
        _("الوصف"),
        max_length=200,
        blank=True
    )

    # خاصية تعرض اسم التصنيف وفق اللغة الحالية
    # @property تسمح باستخدامها كأنها خاصية عادية دون أقواس
    @property
    def display_name(self):
        # تُترجم أسماء التصنيفات الافتراضية عند عرضها
        # أما الأسماء التي يكتبها المستخدم فتعتمد ترجمتها على وجود ترجمة لها
        return gettext(self.name)

    # خاصية تعرض وصف التصنيف مترجمًا عند وجود وصف
    @property
    def display_description(self):

        # إذا كان الوصف موجودًا، نمرره إلى gettext للترجمة
        # وإذا كان فارغًا، نرجع نصًا فارغًا
        return gettext(self.description) if self.description else ""

    # دالة على مستوى الكلاس لإنشاء قائمة التصنيفات المعروضة للمستخدم
    # @classmethod تجعل الدالة تستقبل الكلاس نفسه بدل كائن واحد
    @classmethod
    def display_choices(cls, empty_label):

        # جلب جميع التصنيفات من قاعدة البيانات
        # ثم ترتيبها حسب الاسم الظاهر باللغة الحالية
        # casefold() يساعد على المقارنة النصية دون التأثر بحالة الأحرف
        items = sorted(
            cls.objects.all(),
            key=lambda c: c.display_name.casefold()
        )

        # تجهيز قائمة من أزواج (القيمة، النص المعروض)
        # أول عنصر يمثل الخيار الفارغ مثل "اختر تصنيفًا"
        # وبقية العناصر تحتوي على رقم التصنيف واسمه المعروض
        return [("", str(empty_label))] + [
            (c.pk, c.display_name) for c in items
        ]

    # إعدادات إضافية لنموذج التصنيفات
    class Meta:

        # ترتيب التصنيفات افتراضيًا حسب الاسم المخزن
        ordering = ["name"]

        # الاسم المفرد في لوحة إدارة Django
        verbose_name = _("تصنيف")

        # الاسم عند عرض عدة تصنيفات
        verbose_name_plural = _("التصنيفات")

        # إضافة قيود على البيانات في قاعدة البيانات
        constraints = [

            # منع تكرار اسم التصنيف مع تجاهل اختلاف حالة الأحرف
            # Lower("name") يقارن الاسم بعد تحويله إلى أحرف صغيرة
            models.UniqueConstraint(
                Lower("name"),

                # اسم مميز لهذا القيد في قاعدة البيانات
                name="uniq_category_name_ci",

                # رسالة الخطأ عند محاولة إضافة اسم مكرر
                violation_error_message=_("يوجد تصنيف بنفس الاسم."),
            )
        ]

    # تحديد النص الذي يظهر عند طباعة كائن التصنيف
    def __str__(self):

        # عرض اسم التصنيف المجهز للغة الحالية
        return self.display_name


# إنشاء نموذج الاشتراكات
class Subscription(models.Model):

    # تحديد دورات الفوترة المتاحة للاشتراك
    class BillingCycle(models.TextChoices):

        # فوترة أسبوعية
        WEEKLY = "weekly", _("أسبوعية")

        # فوترة شهرية
        MONTHLY = "monthly", _("شهرية")

        # فوترة كل ثلاثة أشهر
        QUARTERLY = "quarterly", _("ربع سنوية")

        # فوترة سنوية
        YEARLY = "yearly", _("سنوية")

    # تحديد حالات الاشتراك الممكنة
    class Status(models.TextChoices):

        # الاشتراك نشط
        ACTIVE = "active", _("نشط")

        # الاشتراك متوقف مؤقتًا
        PAUSED = "paused", _("متوقف")

        # الاشتراك ملغى
        CANCELLED = "cancelled", _("ملغى")

        # الاشتراك مؤرشف
        ARCHIVED = "archived", _("مؤرشف")

    # ربط الاشتراك بالمستخدم الذي يملكه
    user = models.ForeignKey(
        # استخدام نموذج المستخدم المحدد في إعدادات المشروع
        settings.AUTH_USER_MODEL,

        # حذف اشتراكات المستخدم إذا حُذف المستخدم نفسه
        on_delete=models.CASCADE,

        # يسمح بالوصول إلى اشتراكات المستخدم عبر user.subscriptions
        related_name="subscriptions",

        # اسم الحقل في واجهات Django
        verbose_name=_("المستخدم"),
    )

    # ربط الاشتراك بتصنيف واحد
    category = models.ForeignKey(
        # نموذج التصنيفات الذي يرتبط به الاشتراك
        Category,

        # منع حذف التصنيف إذا كانت هناك اشتراكات مرتبطة به
        on_delete=models.RESTRICT,

        # يسمح بالوصول إلى اشتراكات التصنيف عبر category.subscriptions
        related_name="subscriptions",

        # اسم الحقل في الواجهة
        verbose_name=_("التصنيف"),
    )

    # اسم الخدمة التي يشترك فيها المستخدم، مثل Netflix
    service_name = models.CharField(
        _("اسم الخدمة"),
        max_length=120
    )

    # المبلغ المطلوب دفعه مقابل الاشتراك
    amount = models.DecimalField(
        # اسم الحقل المعروض
        _("المبلغ"),

        # إجمالي عدد الأرقام المسموح بها، بما فيها الأرقام العشرية
        max_digits=10,

        # عدد الأرقام بعد الفاصلة العشرية
        decimal_places=2,

        # التحقق من أن المبلغ لا يقل عن صفر
        validators=[
            MinValueValidator(
                Decimal("0"),
                message=_("لا يمكن أن يكون المبلغ سالبًا.")
            )
        ],
    )

    # العملة المستخدمة في الاشتراك
    currency = models.CharField(
        _("العملة"),

        # رمز العملة يتكون من ثلاثة أحرف
        max_length=3,

        # الخيارات المسموح بها مأخوذة من Currency
        choices=Currency.choices,

        # العملة الافتراضية هي الريال السعودي
        default=Currency.SAR
    )

    # تحديد دورة دفع الاشتراك
    billing_cycle = models.CharField(
        _("دورة الفوترة"),
        max_length=10,

        # السماح فقط بخيارات BillingCycle
        choices=BillingCycle.choices,

        # الدورة الافتراضية شهرية
        default=BillingCycle.MONTHLY
    )

    # تاريخ بداية الاشتراك
    start_date = models.DateField(_("تاريخ البداية"))

    # تاريخ التجديد القادم للاشتراك
    next_renewal_date = models.DateField(_("تاريخ التجديد القادم"))

    # تحديد حالة الاشتراك
    status = models.CharField(
        _("الحالة"),
        max_length=10,

        # الخيارات المتاحة للحالة مأخوذة من Status
        choices=Status.choices,

        # الحالة الافتراضية نشط
        default=Status.ACTIVE
    )

    # تحديد ما إذا كان الاشتراك يتكرر أو يتجدد دوريًا
    # القيمة الافتراضية True تعني أنه متكرر
    is_recurring = models.BooleanField(
        _("متكرر؟"),
        default=True
    )

    # تحديد عدد الأيام التي يسبق بها التذكير موعد التجديد
    reminder_days_before = models.PositiveSmallIntegerField(
        _("التذكير قبل التجديد (بالأيام)"),

        # إرسال التذكير قبل التجديد بثلاثة أيام افتراضيًا
        default=3,

        # السماح بقيمة لا تتجاوز 60 يومًا
        validators=[
            MaxValueValidator(
                60,
                message=_("الحد الأقصى للتذكير 60 يومًا.")
            )
        ],
    )

    # ملاحظات إضافية حول الاشتراك
    # TextField مناسب للنصوص الأطول من الحقول النصية العادية
    # blank=True يسمح بترك الملاحظات فارغة
    notes = models.TextField(
        _("ملاحظات"),
        blank=True
    )

    # حفظ تاريخ إنشاء سجل الاشتراك تلقائيًا
    created_at = models.DateTimeField(
        _("تاريخ الإنشاء"),
        auto_now_add=True
    )

    # تحديث تاريخ آخر تعديل تلقائيًا عند حفظ الاشتراك
    updated_at = models.DateTimeField(
        _("آخر تحديث"),
        auto_now=True
    )

    # إعدادات إضافية لنموذج الاشتراكات
    class Meta:

        # ترتيب الاشتراكات حسب أقرب تاريخ تجديد
        # وإذا تساوى التاريخ، يكون الترتيب حسب اسم الخدمة
        ordering = ["next_renewal_date", "service_name"]

        # الاسم المفرد في لوحة إدارة Django
        verbose_name = _("اشتراك")

        # الاسم عند عرض عدة اشتراكات
        verbose_name_plural = _("الاشتراكات")

        # قيود تتحقق منها قاعدة البيانات
        constraints = [

            # التأكد من أن مبلغ الاشتراك أكبر من أو يساوي صفرًا
            models.CheckConstraint(
                condition=Q(amount__gte=0),

                # اسم القيد
                name="subscription_amount_non_negative",

                # رسالة الخطأ عند مخالفة الشرط
                violation_error_message=_("لا يمكن أن يكون المبلغ سالبًا."),
            ),

            # التأكد من أن تاريخ التجديد لا يسبق تاريخ البداية
            # F("start_date") تشير إلى قيمة حقل start_date نفسه
            # وبذلك تتم مقارنة الحقلين داخل قاعدة البيانات
            models.CheckConstraint(
                condition=Q(next_renewal_date__gte=F("start_date")),

                # اسم القيد
                name="subscription_renewal_not_before_start",

                # رسالة الخطأ عند مخالفة ترتيب التاريخين
                violation_error_message=_("تاريخ التجديد القادم لا يمكن أن يسبق تاريخ البداية."),
            ),
        ]

    # تحديد النص الذي يظهر عند طباعة كائن الاشتراك
    def __str__(self):

        # إرجاع اسم الخدمة بدل عرض تمثيل الكائن الافتراضي
        return self.service_name

    # خاصية تحسب عدد الأيام المتبقية حتى موعد التجديد
    @property
    def days_until_renewal(self):

        # الحصول على تاريخ اليوم حسب إعدادات المنطقة الزمنية في Django
        # ثم طرح تاريخ اليوم من تاريخ التجديد
        # الناتج عدد الأيام:
        # موجب = موعد التجديد في المستقبل
        # صفر = موعد التجديد اليوم
        # سالب = موعد التجديد قد مضى
        return (
            self.next_renewal_date - timezone.localdate()
        ).days

    # خاصية تتحقق مما إذا كان الاشتراك يحتاج إلى مراجعة
    @property
    def needs_review(self):
        # قاعدة العمل:
        # يحتاج الاشتراك إلى مراجعة إذا كانت حالته نشطة
        # وكان تاريخ التجديد القادم قد مضى بالفعل

        # النتيجة True إذا تحقق الشرطان معًا، وإلا False
        return (
            self.status == self.Status.ACTIVE
            and self.next_renewal_date < timezone.localdate()
        )
