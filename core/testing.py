"""Small factories shared by the automated tests (not a test module itself)."""

# استيراد timedelta للتعامل مع الفترات الزمنية وإضافة أو طرح عدد من الأيام
from datetime import timedelta

# استيراد Decimal للتعامل مع الأرقام العشرية بدقة، خصوصًا المبالغ المالية
from decimal import Decimal

# استيراد الدالة get_user_model للحصول على نموذج المستخدم المعتمد في مشروع Django
from django.contrib.auth import get_user_model

# استيراد timezone للتعامل مع التاريخ والوقت وفق إعدادات Django
from django.utils import timezone

# استيراد نموذج الملف الشخصي للمستخدم
from accounts.models import Profile

# استيراد نموذج المدفوعات
from payments.models import Payment

# استيراد نماذج التصنيفات والاشتراكات
from subscriptions.models import Category, Subscription


# تحديد كلمة مرور افتراضية تُستخدم عند إنشاء المستخدمين في الاختبارات
PASSWORD = "Str0ng-Pass!234"


# دالة مساعدة لإنشاء مستخدم جديد مع ملفه الشخصي
# يمكن تمرير البريد الإلكتروني والاسم ونوع الحساب واسم النشاط التجاري
# القيم المكتوبة هنا هي القيم الافتراضية إذا لم نمرر قيمًا أخرى
def make_user(email="user@example.com", name="Tester", account_type="individual", business_name=""):

    # الحصول على نموذج المستخدم المستخدم في المشروع وإنشاء مستخدم جديد
    # username = اسم المستخدم، وemail = البريد الإلكتروني
    # password = كلمة المرور، وfirst_name = الاسم الأول
    user = get_user_model().objects.create_user(
        username=email,
        email=email,
        password=PASSWORD,
        first_name=name
    )

    # إنشاء ملف شخصي مرتبط بالمستخدم الذي أنشأناه
    # user يربط الملف الشخصي بالمستخدم
    # account_type يحدد نوع الحساب
    # business_name يحفظ اسم النشاط التجاري إن وُجد
    Profile.objects.create(
        user=user,
        account_type=account_type,
        business_name=business_name
    )

    # إرجاع المستخدم حتى نتمكن من استخدامه في أجزاء أخرى من الاختبارات
    return user


# دالة مساعدة لإنشاء تصنيف جديد أو الحصول على تصنيف موجود بالاسم نفسه
def make_category(name="تصنيف اختبار"):

    # get_or_create تبحث عن التصنيف بالاسم المحدد
    # إذا كان موجودًا، تُرجع التصنيف الموجود
    # وإذا لم يكن موجودًا، تنشئ تصنيفًا جديدًا
    # [0] تعني أننا نأخذ الكائن فقط من النتيجة، وليس قيمة created
    return Category.objects.get_or_create(name=name)[0]


# دالة مساعدة لإنشاء اشتراك مرتبط بمستخدم
# user هو المستخدم الذي سيملك الاشتراك
# **overrides يسمح بتمرير قيم إضافية أو تغيير القيم الافتراضية
def make_subscription(user, **overrides):

    # الحصول على تاريخ اليوم حسب المنطقة الزمنية في Django
    today = timezone.localdate()

    # تجهيز بيانات الاشتراك الافتراضية داخل قاموس
    data = {
        # ربط الاشتراك بالمستخدم
        "user": user,

        # ربط الاشتراك بتصنيف، وإنشاء التصنيف إذا لم يكن موجودًا
        "category": make_category(),

        # اسم الخدمة التي يشترك فيها المستخدم
        "service_name": "Netflix",

        # مبلغ الاشتراك باستخدام Decimal للحفاظ على دقة المبلغ المالي
        "amount": Decimal("45.00"),

        # عملة الاشتراك: الريال السعودي
        "currency": "SAR",

        # دورة الفوترة: شهرية
        "billing_cycle": "monthly",

        # تاريخ بداية الاشتراك قبل 30 يومًا من اليوم
        "start_date": today - timedelta(days=30),

        # تاريخ التجديد القادم بعد 30 يومًا من اليوم
        "next_renewal_date": today + timedelta(days=30),

        # حالة الاشتراك: نشط
        "status": "active",

        # تحديد أن الاشتراك متكرر ويتجدد بصورة دورية
        "is_recurring": True,

        # إرسال التذكير قبل موعد التجديد بثلاثة أيام
        "reminder_days_before": 3,
    }

    # دمج القيم التي يمررها المستخدم مع البيانات الافتراضية
    # إذا تكرر المفتاح، فإن القيمة الجديدة تستبدل القيمة الافتراضية
    data.update(overrides)

    # إنشاء الاشتراك في قاعدة البيانات باستخدام البيانات النهائية
    return Subscription.objects.create(**data)


# دالة مساعدة لإنشاء عملية دفع مرتبطة بمستخدم
# يمكن تمرير اشتراك اختياري وتغيير البيانات باستخدام **overrides
def make_payment(user, subscription=None, **overrides):

    # الحصول على تاريخ اليوم
    today = timezone.localdate()

    # تجهيز بيانات الدفع الافتراضية
    data = {
        # المستخدم الذي تخصه عملية الدفع
        "user": user,

        # الاشتراك المرتبط بالدفع، وقد تكون قيمته None إذا لم يُمرر اشتراك
        "subscription": subscription,

        # مبلغ الدفع الافتراضي باستخدام Decimal
        "amount": Decimal("45.00"),

        # استخدام عملة الاشتراك إذا كان الاشتراك موجودًا
        # وإذا لم يوجد اشتراك، تكون العملة الافتراضية هي الريال السعودي
        "currency": subscription.currency if subscription else "SAR",

        # تاريخ عملية الدفع
        "payment_date": today,

        # حالة الدفع: مدفوع
        "status": "paid",
    }

    # تطبيق أي قيم إضافية أو بديلة تم تمريرها للدالة
    data.update(overrides)

    # إنشاء عملية الدفع في قاعدة البيانات وإرجاع الكائن الناتج
    return Payment.objects.create(**data)
