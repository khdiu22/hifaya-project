
# استيراد gettext_lazy لدعم ترجمة النصوص حسب اللغة المحددة في المشروع
# نستخدم الرمز _ كاختصار للدالة
from django.utils.translation import gettext_lazy as _

# استيراد إعدادات Django للوصول إلى نموذج المستخدم المعتمد في المشروع
from django.conf import settings

# استيراد ValidationError لعرض أخطاء التحقق من البيانات
from django.core.exceptions import ValidationError

# استيراد models لإنشاء نموذج قاعدة البيانات وتحديد الحقول
from django.db import models

# استيراد Q لإنشاء شروط يمكن دمجها باستخدام OR و AND و NOT
from django.db.models import Q


# إنشاء نموذج الملف الشخصي الإضافي للمستخدم
class Profile(models.Model):
    """
    بيانات إضافية لحساب المستخدم.
    تبقى كلمات المرور داخل نموذج User المدمج في Django،
    وتُخزّن بصورة مشفّرة تجزئيًا (Hashed).
    """

    # تحديد أنواع الحسابات المتاحة باستخدام TextChoices
    # TextChoices تساعدنا على تحديد الخيارات والقيم المسموح بها
    class AccountType(models.TextChoices):

        # القيمة المخزنة في قاعدة البيانات هي individual
        # والنص الذي يظهر للمستخدم هو "فرد"
        INDIVIDUAL = "individual", _("فرد")

        # القيمة المخزنة هي business
        # والنص الذي يظهر للمستخدم هو "منشأة"
        BUSINESS = "business", _("منشأة")

    # تحديد اللغات المتاحة للمستخدم
    class Language(models.TextChoices):

        # رمز اللغة العربية هو ar
        ARABIC = "ar", "العربية"

        # رمز اللغة الإنجليزية هو en
        ENGLISH = "en", "English"

    # ربط الملف الشخصي بمستخدم واحد فقط
    user = models.OneToOneField(
        # استخدام نموذج المستخدم المحدد في إعدادات المشروع
        settings.AUTH_USER_MODEL,

        # عند حذف المستخدم، يُحذف ملفه الشخصي المرتبط به
        on_delete=models.CASCADE,

        # يسمح بالوصول إلى الملف الشخصي من خلال user.profile
        related_name="profile",

        # الاسم الذي يظهر لهذا الحقل في واجهات Django
        verbose_name=_("المستخدم"),
    )

    # تخزين اللغة المفضلة للمستخدم
    preferred_language = models.CharField(
        # اسم الحقل الظاهر في لوحة الإدارة
        _("اللغة المفضلة"),

        # أقصى طول للقيمة هو حرفان، مثل ar و en
        max_length=2,

        # الخيارات المسموح بها مأخوذة من Language
        choices=Language.choices,

        # اللغة الافتراضية هي العربية
        default=Language.ARABIC,
    )

    # تحديد نوع حساب المستخدم: فرد أو منشأة
    account_type = models.CharField(
        # اسم الحقل الظاهر في لوحة الإدارة
        _("نوع الحساب"),

        # أقصى طول للنص المخزن هو 20 حرفًا
        max_length=20,

        # السماح فقط بالخيارات الموجودة في AccountType
        choices=AccountType.choices,

        # نوع الحساب الافتراضي هو فرد
        default=AccountType.INDIVIDUAL,
    )

    # تخزين اسم المنشأة إذا كان الحساب من نوع منشأة
    business_name = models.CharField(
        # اسم الحقل الظاهر في لوحة الإدارة
        _("اسم المنشأة"),

        # أقصى طول لاسم المنشأة هو 150 حرفًا
        max_length=150,

        # السماح بترك الحقل فارغًا في النماذج
        # نتحقق لاحقًا من إلزاميته لحساب المنشأة
        blank=True,
    )

    # تسجيل تاريخ إنشاء الملف الشخصي تلقائيًا
    # auto_now_add يعني أن التاريخ يُحدد عند الإنشاء فقط
    created_at = models.DateTimeField(
        _("تاريخ الإنشاء"),
        auto_now_add=True
    )

    # تسجيل تاريخ آخر تحديث للملف الشخصي
    # auto_now يحدّث التاريخ عند حفظ التغييرات
    updated_at = models.DateTimeField(
        _("آخر تحديث"),
        auto_now=True
    )

    # إعدادات إضافية للنموذج
    class Meta:

        # الاسم المفرد للنموذج في لوحة إدارة Django
        verbose_name = _("ملف شخصي")

        # الاسم الذي يظهر عند الإشارة إلى عدة ملفات شخصية
        verbose_name_plural = _("الملفات الشخصية")

        # إضافة قيود على البيانات في قاعدة البيانات
        constraints = [

            # التحقق من أن نوع الحساب فرد
            # أو أن اسم المنشأة ليس نصًا فارغًا
            models.CheckConstraint(
                condition=Q(account_type="individual") | ~Q(business_name=""),

                # اسم فريد للقيد داخل قاعدة البيانات
                # يُستخدم للتعرف عليه عند إنشاء الترحيلات أو التعامل معه
                name="business_requires_business_name",

                # رسالة الخطأ المرتبطة بمخالفة القيد
                violation_error_message=_("اسم المنشأة مطلوب لحساب المنشأة."),
            )
        ]

    # التحقق من صحة بيانات الملف الشخصي على مستوى النموذج
    def clean(self):

        # تشغيل التحقق الأساسي الذي توفره Django
        super().clean()

        # إذا كان نوع الحساب منشأة
        # وكان اسم المنشأة فارغًا أو مكوّنًا من مسافات فقط
        if (
            self.account_type == self.AccountType.BUSINESS
            and not (self.business_name or "").strip()
        ):

            # إظهار الخطأ عند حقل اسم المنشأة
            raise ValidationError(
                {
                    "business_name": _(
                        "اسم المنشأة مطلوب لحساب المنشأة."
                    )
                }
            )

    # تحديد شكل عرض كائن الملف الشخصي عند طباعته
    # مثلًا عند استخدام print(profile) أو عرضه في لوحة الإدارة
    def __str__(self):

        # إرجاع اسم المستخدم مع نوع الحساب بصيغته المعروضة للمستخدم
        # get_account_type_display() ترجع النص المرتبط بالخيار المحدد
        return f"{self.user} ({self.get_account_type_display()})"
