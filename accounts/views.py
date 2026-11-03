
# استيراد إعدادات Django للوصول إلى إعدادات اللغات وملفات تعريف الارتباط
from django.conf import settings

# استيراد messages لإظهار رسائل النجاح والخطأ للمستخدم
from django.contrib import messages

# استيراد صفحة تسجيل الدخول الجاهزة من Django لتخصيصها
from django.contrib.auth.views import LoginView

# استيراد redirect للانتقال إلى صفحة أخرى
# واستيراد render لعرض صفحة HTML مع تمرير البيانات إليها
from django.shortcuts import redirect, render

# استيراد translation للتعامل مع اللغة النشطة وتغييرها مؤقتًا
from django.utils import translation

# استيراد أداة التحقق من أن رابط إعادة التوجيه آمن ومسموح به
from django.utils.http import url_has_allowed_host_and_scheme

# استيراد gettext_lazy لترجمة الرسائل حسب اللغة
# واستخدام الرمز _ كاختصار للدالة
from django.utils.translation import gettext_lazy as _

# استيراد require_POST للسماح باستدعاء دالة معينة باستخدام POST فقط
from django.views.decorators.http import require_POST

# استيراد نموذجي تسجيل الدخول وإنشاء الحساب
from .forms import LoginForm, RegisterForm

# استيراد نموذج الملف الشخصي للمستخدم
from .models import Profile


# دالة للحصول على اللغة المحفوظة في الملف الشخصي للمستخدم
def saved_language(user):
    # توضيح وظيفة الدالة:
    # ترجع اللغة المحفوظة في الملف الشخصي، مثل ar أو en
    # وإذا لم توجد لغة صالحة، ترجع None

    # محاولة الحصول على الملف الشخصي المرتبط بالمستخدم
    # إذا لم يكن موجودًا، تكون القيمة None بدلًا من حدوث خطأ
    profile = getattr(user, "profile", None)

    # محاولة الحصول على اللغة المفضلة من الملف الشخصي
    # إذا لم يوجد الملف الشخصي أو الحقل، تكون القيمة None
    language = getattr(profile, "preferred_language", None)

    # التأكد من أن اللغة موجودة ضمن اللغات المدعومة في إعدادات المشروع
    # إذا كانت صالحة نرجعها، وإلا نرجع None
    return language if language in dict(settings.LANGUAGES) else None


# دالة لحفظ اللغة في ملف تعريف الارتباط (Cookie) داخل المتصفح
def set_language_cookie(response, language):

    # حفظ رمز اللغة باستخدام اسم وإعدادات Cookie المحددة في Django
    response.set_cookie(

        # اسم ملف تعريف الارتباط المخصص للغة
        settings.LANGUAGE_COOKIE_NAME,

        # قيمة اللغة التي نريد حفظها، مثل ar أو en
        language,

        # مدة صلاحية ملف تعريف الارتباط بالثواني
        max_age=settings.LANGUAGE_COOKIE_AGE,

        # المسار الذي يكون ملف تعريف الارتباط صالحًا ضمنه
        path=settings.LANGUAGE_COOKIE_PATH,

        # النطاق الذي يكون ملف تعريف الارتباط صالحًا له
        domain=settings.LANGUAGE_COOKIE_DOMAIN,

        # إذا كانت True، يُرسل ملف تعريف الارتباط عبر HTTPS فقط
        secure=settings.LANGUAGE_COOKIE_SECURE,

        # إذا كانت True، لا يستطيع JavaScript قراءة ملف تعريف الارتباط
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,

        # تحديد سياسة إرسال ملف تعريف الارتباط مع الطلبات المختلفة
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )


# إنشاء كلاس مخصص لتسجيل الدخول
# يرث الوظائف الأساسية من LoginView في Django
class HifayaLoginView(LoginView):

    # تحديد قالب HTML الذي سيظهر فيه نموذج تسجيل الدخول
    template_name = "accounts/login.html"

    # استخدام نموذج تسجيل الدخول المخصص LoginForm
    authentication_form = LoginForm

    # إذا كان المستخدم مسجل الدخول بالفعل، يُعاد توجيهه إلى الصفحة المناسبة
    # بدلًا من عرض صفحة تسجيل الدخول مرة أخرى
    redirect_authenticated_user = True

    # دالة تُنفذ بعد نجاح التحقق من بيانات تسجيل الدخول
    def form_valid(self, form):

        # تنفيذ سلوك تسجيل الدخول الأصلي الذي توفره Django
        # ثم الحصول على الاستجابة الناتجة
        response = super().form_valid(form)

        # إذا لم يحدد المستخدم خيار "تذكّرني"
        if not form.cleaned_data.get("remember_me"):

            # جعل جلسة تسجيل الدخول تنتهي عند إغلاق المتصفح
            # القيمة 0 تعني أن الجلسة لا تستخدم مدة صلاحية ثابتة
            self.request.session.set_expiry(0)

        # محاولة الحصول على اللغة المحفوظة في حساب المستخدم
        # وإذا لم توجد، استخدام اللغة النشطة في صفحة تسجيل الدخول
        language = saved_language(self.request.user) or translation.get_language()

        # حفظ اللغة المختارة في ملف تعريف الارتباط الخاص باللغة
        set_language_cookie(response, language)

        # تفعيل اللغة المحددة مؤقتًا أثناء تجهيز رسالة الترحيب
        with translation.override(language):

            # إنشاء نص رسالة الترحيب باللغة النشطة وتحويله إلى نص عادي
            welcome = str(_("👋 أهلًا بعودتك إلى حفاية!"))

        # إضافة رسالة نجاح تظهر للمستخدم بعد تسجيل الدخول
        messages.success(self.request, welcome)

        # إرجاع الاستجابة بعد إكمال تسجيل الدخول والإعدادات الإضافية
        return response


# دالة عرض صفحة إنشاء حساب جديد
def register(request):

    # التحقق مما إذا كان المستخدم مسجل الدخول بالفعل
    if request.user.is_authenticated:

        # إذا كان مسجل الدخول، توجيهه إلى لوحة التحكم
        return redirect("core:dashboard")

    # التحقق مما إذا كان الطلب ناتجًا عن إرسال النموذج باستخدام POST
    if request.method == "POST":

        # إنشاء نموذج تسجيل باستخدام البيانات التي أرسلها المستخدم
        form = RegisterForm(request.POST)

        # التحقق من صحة جميع الحقول وقواعد التحقق الموجودة في النموذج
        if form.is_valid():

            # حفظ المستخدم الجديد وملفه الشخصي في قاعدة البيانات
            form.save()

            # إضافة رسالة نجاح بعد إنشاء الحساب
            messages.success(
                request,
                _("🎉 تم إنشاء حسابك بنجاح! سجّل دخولك للبدء.")
            )

            # توجيه المستخدم إلى صفحة تسجيل الدخول
            return redirect("accounts:login")

        # إذا كانت البيانات غير صحيحة، عرض رسالة خطأ للمستخدم
        messages.error(
            request,
            _("❌ تعذّر إنشاء الحساب، راجع الحقول المظللة.")
        )

    else:
        # إذا كانت الصفحة مفتوحة بطلب GET، أنشئ نموذجًا فارغًا
        # واجعل نوع الحساب الافتراضي فردًا
        form = RegisterForm(initial={"account_type": "individual"})

    # عرض صفحة إنشاء الحساب وتمرير النموذج إليها
    # حتى تظهر الحقول وأي أخطاء تحقق عند وجودها
    return render(
        request,
        "accounts/register.html",
        {"form": form}
    )


# السماح باستدعاء هذه الدالة باستخدام طلب POST فقط
# أي طلب بطريقة GET لن يُنفذ الدالة بالطريقة المعتادة
@require_POST
def save_language_preference(request):
    # هذه الدالة تحفظ اللغة المختارة:
    # للزائر تحفظها في Cookie
    # وللمستخدم المسجل تحفظها في Cookie والملف الشخصي

    # الحصول على رمز اللغة المرسل من النموذج
    # إذا لم توجد القيمة، نستخدم نصًا فارغًا
    language = request.POST.get("language", "")

    # الحصول على الرابط الذي نريد العودة إليه بعد حفظ اللغة
    next_url = request.POST.get("next", "")

    # التحقق من أن رابط إعادة التوجيه آمن
    # allowed_hosts يحدد المضيف المسموح به، وهو مضيف الطلب الحالي
    # require_https يطلب HTTPS إذا كان الطلب الحالي يستخدم HTTPS
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):

        # إذا كان الرابط غير آمن أو غير مسموح به، نعود إلى الصفحة الرئيسية
        next_url = "/"

    # تجهيز الاستجابة التي تعيد المستخدم إلى الرابط المحدد
    response = redirect(next_url)

    # التأكد من أن اللغة المطلوبة موجودة ضمن اللغات المدعومة في المشروع
    if language not in dict(settings.LANGUAGES):

        # إذا كانت اللغة غير مدعومة، نعيد الاستجابة دون حفظها
        return response

    # التحقق مما إذا كان المستخدم قد سجل الدخول
    if request.user.is_authenticated:

        # الحصول على الملف الشخصي للمستخدم أو إنشاؤه إذا لم يكن موجودًا
        # المتغير _created يستقبل معلومة هل أُنشئ الملف حديثًا
        # لكنه غير مستخدم في بقية الدالة
        profile, _created = Profile.objects.get_or_create(
            user=request.user
        )

        # التحقق مما إذا كانت اللغة المختارة تختلف عن اللغة المحفوظة
        if profile.preferred_language != language:

            # تحديث اللغة المفضلة في كائن الملف الشخصي
            profile.preferred_language = language

            # حفظ الحقل الذي تغير فقط بدل حفظ جميع الحقول
            profile.save(update_fields=["preferred_language"])

    # حفظ اللغة في Cookie سواء كان المستخدم زائرًا أو مسجل الدخول
    set_language_cookie(response, language)

    # إرجاع الاستجابة التي تتضمن إعادة التوجيه وملف تعريف الارتباط
    return response
