
# استيراد gettext_lazy لدعم ترجمة النصوص حسب اللغة المحددة في المشروع
from django.utils.translation import gettext_lazy as _

# استيراد forms لإنشاء نماذج الإدخال والتحقق من بيانات المستخدم
from django import forms

# استيراد translation لمعرفة اللغة النشطة في المشروع
from django.utils import translation

# استيراد settings للوصول إلى إعدادات Django، مثل اللغات المدعومة
from django.conf import settings

# استيراد get_user_model للحصول على نموذج المستخدم المعتمد في المشروع
from django.contrib.auth import get_user_model

# استيراد نموذج تسجيل الدخول الجاهز من Django
from django.contrib.auth.forms import AuthenticationForm

# استيراد أداة التحقق من قوة كلمة المرور
from django.contrib.auth.password_validation import validate_password

# استيراد ValidationError للتعامل مع أخطاء التحقق من البيانات
from django.core.exceptions import ValidationError

# استيراد transaction للتحكم في العمليات التي تُحفظ في قاعدة البيانات
from django.db import transaction

# استيراد نموذج الملف الشخصي من التطبيق الحالي
from .models import Profile


# الحصول على نموذج المستخدم المستخدم في إعدادات المشروع
User = get_user_model()


# إنشاء نموذج تسجيل حساب جديد
class RegisterForm(forms.Form):

    # حقل الاسم
    name = forms.CharField(label=_("الاسم"), max_length=150)

    # حقل البريد الإلكتروني
    email = forms.EmailField(label=_("البريد الإلكتروني"), max_length=150)

    # حقل كلمة المرور الأولى
    password1 = forms.CharField(
        label=_("كلمة المرور"),
        strip=False,
        widget=forms.PasswordInput
    )

    # حقل تأكيد كلمة المرور
    password2 = forms.CharField(
        label=_("تأكيد كلمة المرور"),
        strip=False,
        widget=forms.PasswordInput
    )

    # حقل اختيار نوع الحساب
    account_type = forms.ChoiceField(
        label=_("نوع الحساب"),
        choices=Profile.AccountType.choices,
        widget=forms.RadioSelect
    )

    # حقل اسم المنشأة
    business_name = forms.CharField(
        label=_("اسم المنشأة"),
        max_length=150,
        required=False,
        help_text=_("مطلوب إذا كان نوع الحساب «منشأة»، ويُترك فارغًا للأفراد."),
    )

    # التحقق من البريد الإلكتروني
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if (
            User.objects.filter(username__iexact=email).exists()
            or User.objects.filter(email__iexact=email).exists()
        ):
            raise ValidationError(_("هذا البريد الإلكتروني مسجّل مسبقًا."))

        return email

    # التحقق من البيانات المترابطة في النموذج
    def clean(self):
        cleaned = super().clean()

        p1, p2 = cleaned.get("password1"), cleaned.get("password2")

        # التحقق من تطابق كلمتي المرور
        if p1 and p2 and p1 != p2:
            self.add_error("password2", _("كلمتا المرور غير متطابقتين."))

        # التحقق من قوة كلمة المرور
        elif p1:
            candidate = User(
                username=cleaned.get("email", ""),
                email=cleaned.get("email", ""),
                first_name=cleaned.get("name", "")
            )

            try:
                validate_password(p1, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)

        # التحقق من نوع الحساب واسم المنشأة
        account_type = cleaned.get("account_type")
        business_name = (cleaned.get("business_name") or "").strip()

        if account_type == Profile.AccountType.BUSINESS and not business_name:
            self.add_error(
                "business_name",
                _("اسم المنشأة مطلوب لحساب المنشأة.")
            )

        if account_type == Profile.AccountType.INDIVIDUAL:
            business_name = ""

        cleaned["business_name"] = business_name

        return cleaned

    # حفظ المستخدم والملف الشخصي ضمن معاملة واحدة
    @transaction.atomic
    def save(self):
        data = self.cleaned_data

        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password1"],
            first_name=data["name"],
        )

        # تحديد اللغة المفضلة للمستخدم
        language = (translation.get_language() or "ar")[:2]

        Profile.objects.create(
            user=user,
            account_type=data["account_type"],
            business_name=data["business_name"],
            preferred_language=(
                language if language in dict(settings.LANGUAGES) else "ar"
            ),
        )

        return user


# إنشاء نموذج تسجيل الدخول
class LoginForm(AuthenticationForm):

    # حقل البريد الإلكتروني
    username = forms.CharField(
        label=_("البريد الإلكتروني"),
        widget=forms.TextInput(attrs={
            "autofocus": True,
            "autocomplete": "email"
        }),
    )

    # حقل كلمة المرور
    password = forms.CharField(
        label=_("كلمة المرور"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password"
        }),
    )

    # خيار تذكر تسجيل الدخول
    remember_me = forms.BooleanField(
        required=False,
        label=_("تذكّرني على هذا الجهاز")
    )

    # رسائل أخطاء تسجيل الدخول
    error_messages = {
        "invalid_login": _("البريد الإلكتروني أو كلمة المرور غير صحيحة."),
        "inactive": _("هذا الحساب غير مفعّل."),
    }

    # تنظيف البريد الإلكتروني المدخل
    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
