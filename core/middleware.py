
# استيراد إعدادات المشروع للوصول إلى اللغات المدعومة في Django
from django.conf import settings

# استيراد أدوات التحكم في لغة الترجمة الحالية
from django.utils import translation


# Middleware يفعّل اللغة المحفوظة في الملف الشخصي للمستخدم المسجل دخوله
# بحيث تظهر له لغته المفضلة حتى لو استخدم متصفحًا أو جهازًا مختلفًا
class UserLanguageMiddleware:

    # تُنفّذ عند إنشاء الـ Middleware
    # ونحفظ فيها الدالة التي تستقبل الطلب وتكمل معالجته
    def __init__(self, get_response):
        self.get_response = get_response

    # تُنفّذ مع كل طلب يصل إلى التطبيق
    def __call__(self, request):

        # محاولة الحصول على المستخدم المرتبط بالطلب
        # getattr تمنع حدوث خطأ إذا لم يكن الكائن يحتوي على الخاصية user
        user = getattr(request, "user", None)

        # التأكد من وجود المستخدم وأنه سجّل الدخول
        if user is not None and user.is_authenticated:

            # محاولة الوصول إلى الملف الشخصي المرتبط بالمستخدم
            profile = getattr(user, "profile", None)

            # الحصول على اللغة المفضلة المحفوظة في الملف الشخصي
            language = getattr(profile, "preferred_language", None)

            # التأكد من أن اللغة المحفوظة ضمن اللغات المعتمدة في إعدادات المشروع
            if language in dict(settings.LANGUAGES):

                # تفعيل اللغة المفضلة للطلب الحالي
                translation.activate(language)

                # حفظ رمز اللغة النشطة في الطلب حتى تستطيع الأجزاء الأخرى قراءته
                request.LANGUAGE_CODE = translation.get_language()

        # تمرير الطلب إلى بقية سلسلة المعالجة وإرجاع الاستجابة الناتجة
        return self.get_response(request)


# Middleware يعيد إعداد اللغة بعد انتهاء معالجة كل طلب
# لمنع بقاء لغة طلب سابق مفعّلة في سياق التنفيذ نفسه
class ResetLanguageMiddleware:

    # تُنفّذ عند إنشاء الـ Middleware
    # ونحفظ فيها الدالة المسؤولة عن متابعة معالجة الطلب
    def __init__(self, get_response):
        self.get_response = get_response

    # تُنفّذ مع كل طلب
    def __call__(self, request):

        try:
            # متابعة معالجة الطلب وإرجاع الاستجابة
            return self.get_response(request)

        finally:
            # إلغاء تفعيل اللغة الحالية بعد انتهاء المعالجة،
            # حتى لا تنتقل لغة طلب سابق إلى عمليات أخرى
            # يُعاد تنفيذ هذا الجزء حتى لو حدث استثناء أثناء معالجة الطلب
            translation.deactivate()
