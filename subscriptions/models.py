from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext


class Currency(models.TextChoices):
    SAR = "SAR", _("ريال سعودي (SAR)")
    USD = "USD", _("دولار أمريكي (USD)")
    EUR = "EUR", _("يورو (EUR)")
    GBP = "GBP", _("جنيه إسترليني (GBP)")
    AED = "AED", _("درهم إماراتي (AED)")


class Category(models.Model):
    name = models.CharField(_("اسم التصنيف"), max_length=80)
    description = models.CharField(_("الوصف"), max_length=200, blank=True)

    @property
    def display_name(self):
        """Default categories are stored in Arabic and translated for display; your own names stay as typed."""
        return gettext(self.name)

    @property
    def display_description(self):
        return gettext(self.description) if self.description else ""

    @classmethod
    def display_choices(cls, empty_label):
        """(id, label) pairs sorted by the name shown in the current language."""
        items = sorted(cls.objects.all(), key=lambda c: c.display_name.casefold())
        return [("", str(empty_label))] + [(c.pk, c.display_name) for c in items]

    class Meta:
        ordering = ["name"]
        verbose_name = _("تصنيف")
        verbose_name_plural = _("التصنيفات")
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="uniq_category_name_ci",
                violation_error_message=_("يوجد تصنيف بنفس الاسم."),
            )
        ]

    def __str__(self):
        return self.display_name


class Subscription(models.Model):
    class BillingCycle(models.TextChoices):
        WEEKLY = "weekly", _("أسبوعية")
        MONTHLY = "monthly", _("شهرية")
        QUARTERLY = "quarterly", _("ربع سنوية")
        YEARLY = "yearly", _("سنوية")

    class Status(models.TextChoices):
        ACTIVE = "active", _("نشط")
        PAUSED = "paused", _("متوقف")
        CANCELLED = "cancelled", _("ملغى")
        ARCHIVED = "archived", _("مؤرشف")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name=_("المستخدم"),
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name="subscriptions",
        verbose_name=_("التصنيف"),
    )
    service_name = models.CharField(_("اسم الخدمة"), max_length=120)
    amount = models.DecimalField(
        _("المبلغ"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"), message=_("لا يمكن أن يكون المبلغ سالبًا."))],
    )
    currency = models.CharField(_("العملة"), max_length=3, choices=Currency.choices, default=Currency.SAR)
    billing_cycle = models.CharField(
        _("دورة الفوترة"), max_length=10, choices=BillingCycle.choices, default=BillingCycle.MONTHLY
    )
    start_date = models.DateField(_("تاريخ البداية"))
    next_renewal_date = models.DateField(_("تاريخ التجديد القادم"))
    status = models.CharField(_("الحالة"), max_length=10, choices=Status.choices, default=Status.ACTIVE)
    is_recurring = models.BooleanField(_("متكرر؟"), default=True)
    reminder_days_before = models.PositiveSmallIntegerField(
        _("التذكير قبل التجديد (بالأيام)"),
        default=3,
        validators=[MaxValueValidator(60, message=_("الحد الأقصى للتذكير 60 يومًا."))],
    )
    notes = models.TextField(_("ملاحظات"), blank=True)
    created_at = models.DateTimeField(_("تاريخ الإنشاء"), auto_now_add=True)
    updated_at = models.DateTimeField(_("آخر تحديث"), auto_now=True)

    class Meta:
        ordering = ["next_renewal_date", "service_name"]
        verbose_name = _("اشتراك")
        verbose_name_plural = _("الاشتراكات")
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="subscription_amount_non_negative",
                violation_error_message=_("لا يمكن أن يكون المبلغ سالبًا."),
            ),
            models.CheckConstraint(
                condition=Q(next_renewal_date__gte=F("start_date")),
                name="subscription_renewal_not_before_start",
                violation_error_message=_("تاريخ التجديد القادم لا يمكن أن يسبق تاريخ البداية."),
            ),
        ]

    def __str__(self):
        return self.service_name

    @property
    def days_until_renewal(self):
        return (self.next_renewal_date - timezone.localdate()).days

    @property
    def needs_review(self):
        """Business rule: an ACTIVE subscription whose renewal date has already passed."""
        return self.status == self.Status.ACTIVE and self.next_renewal_date < timezone.localdate()
