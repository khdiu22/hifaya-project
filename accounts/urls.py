

# استيراد صفحة تسجيل الخروج الجاهزة من Django
from django.contrib.auth.views import LogoutView

# استيراد path لإنشاء مسارات URL وربطها بالدوال أو الصفحات
from django.urls import path

# استيراد ملف views من التطبيق الحالي accounts
# يحتوي على الدوال المسؤولة عن تنفيذ وظائف الحسابات
from . import views


# تحديد مساحة أسماء التطبيق
# نستخدمها للتمييز بين المسارات إذا وُجدت تطبيقات أخرى لديها أسماء مشابهة
# مثال: accounts:login
app_name = "accounts"


# قائمة المسارات التي تخص تطبيق الحسابات
urlpatterns = [

    # عند فتح /register/ يتم استدعاء دالة register الموجودة في views.py
    # name="register" اسم مختصر يمكن استخدامه في القوالب أو إعادة التوجيه
    path("register/", views.register, name="register"),

    # عند فتح /login/ يتم استخدام HifayaLoginView
    # as_view() تحوّل الكلاس إلى View قابلة للاستخدام داخل المسارات
    # name="login" هو الاسم الذي نستخدمه للإشارة إلى هذا المسار
    path("login/", views.HifayaLoginView.as_view(), name="login"),

    # عند فتح /logout/ يتم استخدام صفحة تسجيل الخروج الجاهزة من Django
    # as_view() تحوّل LogoutView إلى View
    # name="logout" هو الاسم المختصر لمسار تسجيل الخروج
    path("logout/", LogoutView.as_view(), name="logout"),

    # مسار لحفظ اللغة المفضلة التي يختارها المستخدم
    path(
        "save-language/",

        # الدالة التي تستقبل الطلب وتنفّذ عملية حفظ تفضيل اللغة
        views.save_language_preference,

        # الاسم المختصر للمسار لاستخدامه داخل المشروع
        name="save_language_preference",
    ),
]
