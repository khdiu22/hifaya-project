from django.utils.translation import gettext_lazy as _
from django import forms
from django.db.models import Q

from core.forms import date_field
from subscriptions.models import Subscription

from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = [
            "subscription",
            "amount",
            "currency",
            "payment_date",
            "payment_method",
            "reference",
            "status",
            "notes",
        ]
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}),
            "payment_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.instance.user = user  # needed by Payment.clean() ownership checks
        self.fields["payment_date"].input_formats = ["%Y-%m-%d"]
        # Only the user's own subscriptions (archived ones only if already linked).
        own = Subscription.objects.filter(user=user)
        current = self.instance.subscription_id
        if current:
            own = own.filter(~Q(status=Subscription.Status.ARCHIVED) | Q(pk=current))
        else:
            own = own.exclude(status=Subscription.Status.ARCHIVED)
        self.fields["subscription"].queryset = own.order_by("service_name")
        self.fields["subscription"].empty_label = _("بدون اشتراك محدد")
        self.fields["subscription"].required = False


class PaymentFilterForm(forms.Form):
    ORDERING = [
        ("-date", _("التاريخ (الأحدث أولًا)")),
        ("date", _("التاريخ (الأقدم أولًا)")),
        ("-amount", _("المبلغ (الأعلى أولًا)")),
        ("amount", _("المبلغ (الأقل أولًا)")),
    ]
    SHOW = [("active", _("الدفعات الحالية")), ("archived", _("المؤرشفة فقط")), ("all", _("الكل"))]

    subscription = forms.ModelChoiceField(
        label=_("الاشتراك"), queryset=Subscription.objects.none(), required=False, empty_label=_("كل الاشتراكات")
    )
    status = forms.ChoiceField(
        label=_("الحالة"), required=False, choices=[("", _("كل الحالات"))] + list(Payment.Status.choices)
    )
    date_from = date_field(_("من تاريخ"))
    date_to = date_field(_("إلى تاريخ"))
    show = forms.ChoiceField(label=_("العرض"), required=False, choices=SHOW)
    ordering = forms.ChoiceField(label=_("الترتيب"), required=False, choices=ORDERING)
    review = forms.BooleanField(label=_("تحتاج إلى مراجعة فقط"), required=False)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subscription"].queryset = Subscription.objects.filter(user=user).order_by("service_name")

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("date_from"), cleaned.get("date_to")
        if start and end and start > end:
            self.add_error("date_to", _("تاريخ النهاية يجب ألا يسبق تاريخ البداية."))
        return cleaned


class ImportForm(forms.Form):
    file = forms.FileField(label=_("ملف JSON"), widget=forms.ClearableFileInput(attrs={"accept": ".json,application/json"}))
