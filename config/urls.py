
# استيراد إعدادات المشروع من ملف settings.py
# نحتاجها لمعرفة إعدادات مثل DEBUG ومسارات الملفات
from django.conf import settings

# استيراد دالة تساعد على إضافة مسارات لخدمة ملفات Media أثناء التطوير
from django.conf.urls.static import static

# استيراد لوحة الإدارة الافتراضية في Django
from django.contrib import admin

# استيراد include لتضمين مسارات التطبيقات الأخرى
# واستيراد path لإنشاء مسارات URL جديدة
from django.urls import include, path

# استيراد serve لتقديم الملفات من مجلد محدد
from django.views.static import serve


# قائمة المسارات الرئيسية للمشروع
# يمر Django على هذه القائمة للعثور على المسار المناسب لكل طلب
urlpatterns = [

    # فتح لوحة إدارة Django عند زيارة /admin/
    path("admin/", admin.site.urls),

    # توفير مسارات Django الخاصة بتغيير اللغة
    # تُستخدم عادةً مع نماذج أو روابط تغيير اللغة
    path("i18n/", include("django.conf.urls.i18n")),

    # ربط جميع المسارات الموجودة في accounts/urls.py
    # بأي رابط يبدأ بـ /accounts/
    path("accounts/", include("accounts.urls")),

    # ربط مسارات تطبيق الاشتراكات
    # بأي رابط يبدأ بـ /subscriptions/
    path("subscriptions/", include("subscriptions.urls")),

    # ربط مسارات تطبيق المدفوعات
    # بأي رابط يبدأ بـ /payments/
    path("payments/", include("payments.urls")),

    # ربط مسارات تطبيق الإشعارات
    # بأي رابط يبدأ بـ /notifications/
    path("notifications/", include("notifications.urls")),

    # ربط مسارات تطبيق التقارير
    # بأي رابط يبدأ بـ /reports/
    path("reports/", include("reports.urls")),

    # تقديم الملفات الثابتة من مجلد static الموجود في المشروع
    # هذا المسار يعمل عند طلب ملف يبدأ رابطه بـ /static/
    # serve هي الدالة المسؤولة عن تقديم الملف المطلوب
    # document_root يحدد المجلد الذي ستُقرأ منه الملفات
    # ملاحظة: هذا المسار مُعرّف هنا دون شرط DEBUG
    path(
        "static/<path:path>",
        serve,
        {"document_root": settings.BASE_DIR / "static"},
    ),

    # ربط المسارات الرئيسية الموجودة في core/urls.py
    # لأن البادئة فارغة، يمكن أن تتعامل هذه المسارات مع روابط مثل /
    path("", include("core.urls")),
]


# التحقق مما إذا كان المشروع يعمل في وضع التطوير
# DEBUG = True يعني أن وضع التصحيح مفعّل
if settings.DEBUG:

    # إضافة مسارات لتقديم ملفات Media المرفوعة أثناء التطوير فقط
    # settings.MEDIA_URL هو الجزء الذي يبدأ به رابط الملف
    # settings.MEDIA_ROOT هو المجلد الفعلي الذي تُحفظ فيه الملفات
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
