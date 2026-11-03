
# استيراد gettext_lazy لجعل النصوص قابلة للترجمة حسب لغة المستخدم
from django.utils.translation import gettext_lazy as _

# استيراد أدوات إنشاء النماذج والحقول في Django
from django import forms

# استيراد Q لبناء شروط متعددة داخل استعلامات قاعدة البيانات
from django.db.models import Q

# استيراد دالة إنشاء حقل تاريخ مشتركة من تطبيق core
from core.forms import date_field

# استيراد موديل الاشتراكات لربط الدفعات بالاشتراكات
from subscriptions.models import Subscription

# استيراد موديل الدفعات
from .models import Payment


# نموذج إضافة وتعديل الدفعات
# ModelForm ينشئ حقول النموذج اعتمادًا على موديل Payment
class PaymentForm(forms.ModelForm):

    # إعدادات النموذج وربطه بموديل Payment
    class Meta:
        model = Payment

        # تحديد الحقول التي ستظهر في النموذج
        fields = [
            "subscription",    # الاشتراك المرتبط بالدفعة
            "amount",          # مبلغ الدفعة
            "currency",        # العملة
            "payment_date",    # تاريخ الدفع
            "payment_method",  # طريقة الدفع
            "reference",       # الرقم المرجعي للدفعة
            "status",          # حالة الدفعة
            "notes",           # ملاحظات إضافية
        ]

        # تخصيص شكل بعض الحقول في واجهة HTML
        widgets = {
            # حقل رقمي يسمح بإدخال المبلغ بخطوات مقدارها 0.01
            # inputmode decimal يساعد الأجهزة على إظهار لوحة أرقام عشرية
            "amount": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "inputmode": "decimal",
                }
            ),

            # عرض حقل التاريخ باستخدام أداة اختيار التاريخ في المتصفح
            # وتحديد تنسيق التاريخ المستخدم عند عرض القيمة
            "payment_date": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),

            # عرض الملاحظات في مربع نص متعدد الأسطر بارتفاع 3 أسطر
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    # تهيئة النموذج عند إنشائه
    # user مطلوب حتى نعرف المستخدم الذي يضيف الدفعة أو يعدلها
    def __init__(self, *args, user, **kwargs):

        # تشغيل تهيئة ModelForm الأصلية في Django
        super().__init__(*args, **kwargs)

        # حفظ المستخدم الحالي لاستخدامه في التحقق من البيانات
        self.user = user

        # تعيين المستخدم على نسخة الدفعة الحالية
        # لأن Payment.clean() يحتاج إلى معرفة مالك الدفعة للتحقق من الملكية
        self.instance.user = user

        # تحديد تنسيق التاريخ المقبول عند إرسال النموذج
        self.fields["payment_date"].input_formats = ["%Y-%m-%d"]

        # جلب اشتراكات المستخدم الحالي فقط
        own = Subscription.objects.filter(user=user)

        # معرفة رقم الاشتراك المرتبط بالدفعة الحالية إن وجد
        current = self.instance.subscription_id

        # إذا كانت الدفعة مرتبطة باشتراك بالفعل
        if current:

            # السماح باختيار الاشتراكات غير المؤرشفة،
            # مع الإبقاء على الاشتراك الحالي ضمن الخيارات حتى لو أُرشف
            own = own.filter(
                ~Q(status=Subscription.Status.ARCHIVED) | Q(pk=current)
            )

        else:
            # إذا لم تكن الدفعة مرتبطة باشتراك،
            # نستبعد الاشتراكات المؤرشفة من الخيارات
            own = own.exclude(status=Subscription.Status.ARCHIVED)

        # تحديد الاشتراكات التي تظهر في القائمة المنسدلة
        # وترتيبها حسب اسم الخدمة
        self.fields["subscription"].queryset = own.order_by("service_name")

        # النص الذي يظهر كخيار فارغ في قائمة الاشتراكات
        self.fields["subscription"].empty_label = _("بدون اشتراك محدد")

        # جعل اختيار الاشتراك اختياريًا
        self.fields["subscription"].required = False


# نموذج تصفية الدفعات في صفحة العرض
# هذا النموذج يتحقق من مدخلات التصفية ولا ينشئ سجل دفعة جديدًا
class PaymentFilterForm(forms.Form):

    # خيارات ترتيب الدفعات حسب التاريخ أو المبلغ
    # القيمة الأولى هي القيمة التي يستخدمها الكود،
    # والقيمة الثانية هي النص الذي يظهر للمستخدم
    ORDERING = [
        ("-date", _("التاريخ (الأحدث أولًا)")),
        ("date", _("التاريخ (الأقدم أولًا)")),
        ("-amount", _("المبلغ (الأعلى أولًا)")),
        ("amount", _("المبلغ (الأقل أولًا)")),
    ]

    # خيارات عرض الدفعات حسب حالتها الأرشيفية
    SHOW = [
        ("active", _("الدفعات الحالية")),
        ("archived", _("المؤرشفة فقط")),
        ("all", _("الكل")),
    ]

    # اختيار اشتراك لتصفية الدفعات المرتبطة به
    # يبدأ الاستعلام فارغًا حتى يتم تحديد اشتراكات المستخدم في __init__
    subscription = forms.ModelChoiceField(
        label=_("الاشتراك"),
        queryset=Subscription.objects.none(),
        required=False,
        empty_label=_("كل الاشتراكات"),
    )

    # تصفية الدفعات حسب الحالة
    # الخيار الفارغ يعني عدم التقييد بحالة معينة
    status = forms.ChoiceField(
        label=_("الحالة"),
        required=False,
        choices=[("", _("كل الحالات"))] + list(Payment.Status.choices),
    )

    # حقل تحديد بداية الفترة الزمنية للتصفية
    date_from = date_field(_("من تاريخ"))

    # حقل تحديد نهاية الفترة الزمنية للتصفية
    date_to = date_field(_("إلى تاريخ"))

    # تحديد ما إذا كان العرض للدفعات الحالية أو المؤرشفة أو الكل
    show = forms.ChoiceField(
        label=_("العرض"),
        required=False,
        choices=SHOW,
    )

    # تحديد طريقة ترتيب النتائج
    ordering = forms.ChoiceField(
        label=_("الترتيب"),
        required=False,
        choices=ORDERING,
    )

    # خيار لتصفية الدفعات التي تحتاج إلى مراجعة فقط
    # required=False يعني أن تفعيله ليس إلزاميًا
    review = forms.BooleanField(
        label=_("تحتاج إلى مراجعة فقط"),
        required=False,
    )

    # تهيئة نموذج التصفية بناءً على المستخدم الحالي
    def __init__(self, *args, user, **kwargs):

        # تشغيل التهيئة الأصلية للنموذج
        super().__init__(*args, **kwargs)

        # حصر خيارات الاشتراك في اشتراكات المستخدم الحالي فقط
        # وترتيبها حسب اسم الخدمة
        self.fields["subscription"].queryset = (
            Subscription.objects.filter(user=user).order_by("service_name")
        )

    # التحقق من البيانات التي تعتمد على أكثر من حقل
    def clean(self):

        # استخراج البيانات بعد تنفيذ التحقق الأساسي لكل حقل
        cleaned = super().clean()

        # الحصول على تاريخ البداية وتاريخ النهاية
        start, end = cleaned.get("date_from"), cleaned.get("date_to")

        # إذا أُدخل التاريخان وكانت البداية بعد النهاية،
        # نضيف خطأ إلى حقل تاريخ النهاية
        if start and end and start > end:
            self.add_error(
                "date_to",
                _("تاريخ النهاية يجب ألا يسبق تاريخ البداية."),
            )

        # إرجاع البيانات التي اجتازت التحقق
        return cleaned


# نموذج رفع ملف لاستيراد بيانات بصيغة JSON
class ImportForm(forms.Form):

    # حقل رفع الملف، مع إظهار تسمية عربية
    # accept يوجّه نافذة اختيار الملفات نحو ملفات JSON
    file = forms.FileField(
        label=_("ملف JSON"),
        widget=forms.ClearableFileInput(
            attrs={"accept": ".json,application/json"}
        ),
    )
