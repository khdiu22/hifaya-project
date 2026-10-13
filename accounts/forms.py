from django.utils.translation import gettext_lazy as _
from django import forms
from django.utils import translation
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Profile

User = get_user_model()


class RegisterForm(forms.Form):
    name = forms.CharField(label=_("الاسم"), max_length=150)
    email = forms.EmailField(label=_("البريد الإلكتروني"), max_length=150)
    password1 = forms.CharField(label=_("كلمة المرور"), strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("تأكيد كلمة المرور"), strip=False, widget=forms.PasswordInput)
    account_type = forms.ChoiceField(
        label=_("نوع الحساب"), choices=Profile.AccountType.choices, widget=forms.RadioSelect
    )
    business_name = forms.CharField(
        label=_("اسم المنشأة"),
        max_length=150,
        required=False,
        help_text=_("مطلوب إذا كان نوع الحساب «منشأة»، ويُترك فارغًا للأفراد."),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("هذا البريد الإلكتروني مسجّل مسبقًا."))
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", _("كلمتا المرور غير متطابقتين."))
        elif p1:
            candidate = User(username=cleaned.get("email", ""), email=cleaned.get("email", ""), first_name=cleaned.get("name", ""))
            try:
                validate_password(p1, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)

        # Conditional rule enforced on the SERVER (no JavaScript involved).
        account_type = cleaned.get("account_type")
        business_name = (cleaned.get("business_name") or "").strip()
        if account_type == Profile.AccountType.BUSINESS and not business_name:
            self.add_error("business_name", _("اسم المنشأة مطلوب لحساب المنشأة."))
        if account_type == Profile.AccountType.INDIVIDUAL:
            business_name = ""
        cleaned["business_name"] = business_name
        return cleaned

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["email"],
            email=data["email"],
            password=data["password1"],
            first_name=data["name"],
        )
        language = (translation.get_language() or "ar")[:2]
        Profile.objects.create(
            user=user,
            account_type=data["account_type"],
            business_name=data["business_name"],
            preferred_language=language if language in dict(settings.LANGUAGES) else "ar",
        )
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_("البريد الإلكتروني"),
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    password = forms.CharField(
        label=_("كلمة المرور"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    remember_me = forms.BooleanField(required=False, label=_("تذكّرني على هذا الجهاز"))

    error_messages = {
        "invalid_login": _("البريد الإلكتروني أو كلمة المرور غير صحيحة."),
        "inactive": _("هذا الحساب غير مفعّل."),
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
