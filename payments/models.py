from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from subscriptions.models import Currency, Subscription


class Payment(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", _("مدفوعة")
        PENDING = "pending", _("قيد الانتظار")
        FAILED = "failed", _("فاشلة")
        REFUNDED = "refunded", _("مستردة")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments", verbose_name=_("المستخدم")
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name=_("الاشتراك المرتبط"),
    )
    amount = models.DecimalField(
        _("المبلغ"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"), message=_("لا يمكن أن يكون المبلغ سالبًا."))],
    )
    currency = models.CharField(_("العملة"), max_length=3, choices=Currency.choices, default=Currency.SAR)
    payment_date = models.DateField(_("تاريخ الدفع"))
    payment_method = models.CharField(_("طريقة الدفع"), max_length=50, blank=True)
    reference = models.CharField(_("مرجع العملية"), max_length=100, blank=True)
    status = models.CharField(_("الحالة"), max_length=10, choices=Status.choices, default=Status.PAID)
    review_required = models.BooleanField(_("تحتاج إلى مراجعة"), default=False)
    review_reason = models.CharField(_("سبب المراجعة"), max_length=255, blank=True)
    notes = models.TextField(_("ملاحظات"), blank=True)
    is_archived = models.BooleanField(_("مؤرشفة"), default=False)
    created_at = models.DateTimeField(_("تاريخ التسجيل"), auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]
        verbose_name = _("دفعة")
        verbose_name_plural = _("المدفوعات")
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="payment_amount_non_negative",
                violation_error_message=_("لا يمكن أن يكون المبلغ سالبًا."),
            )
        ]

    def clean(self):
        super().clean()
        if self.subscription_id and self.user_id:
            if self.subscription.user_id != self.user_id:
                raise ValidationError({"subscription": _("لا يمكنك ربط دفعة باشتراك لا يخصك.")})
            if self.currency and self.subscription.currency != self.currency:
                raise ValidationError(
                    {"currency": _("عملة الدفعة يجب أن تطابق عملة الاشتراك (%(currency)s).") % {"currency": self.subscription.currency}}
                )

    def __str__(self):
        return f"#{self.pk} {self.amount} {self.currency}"
