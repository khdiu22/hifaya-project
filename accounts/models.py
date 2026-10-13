from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Profile(models.Model):
    """Extra account data. Passwords stay in Django's built-in User (hashed)."""

    class AccountType(models.TextChoices):
        INDIVIDUAL = "individual", _("فرد")
        BUSINESS = "business", _("منشأة")

    class Language(models.TextChoices):
        ARABIC = "ar", "العربية"
        ENGLISH = "en", "English"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("المستخدم"),
    )

    preferred_language = models.CharField(
        _("اللغة المفضلة"),
        max_length=2,
        choices=Language.choices,
        default=Language.ARABIC,
    )

    account_type = models.CharField(
        _("نوع الحساب"),
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.INDIVIDUAL,
    )

    business_name = models.CharField(
        _("اسم المنشأة"),
        max_length=150,
        blank=True,
    )

    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("آخر تحديث"), auto_now=True)

    class Meta:
        verbose_name = _("ملف شخصي")
        verbose_name_plural = _("الملفات الشخصية")
        constraints = [
            models.CheckConstraint(
                condition=Q(account_type="individual") | ~Q(business_name=""),
                name="business_requires_business_name",
                violation_error_message=_("اسم المنشأة مطلوب لحساب المنشأة."),
            )
        ]

    def clean(self):
        super().clean()
        if (
            self.account_type == self.AccountType.BUSINESS
            and not (self.business_name or "").strip()
        ):
            raise ValidationError(
                {"business_name": _("اسم المنشأة مطلوب لحساب المنشأة.")}
            )

    def __str__(self):
        return f"{self.user} ({self.get_account_type_display()})"
