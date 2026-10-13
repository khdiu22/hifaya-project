from django.utils.translation import gettext_lazy as _
from django import forms
from django.utils import timezone

from core.forms import date_field

from .models import Category, Subscription


class SubscriptionForm(forms.ModelForm):
    is_recurring = forms.TypedChoiceField(
        label=_("هل الاشتراك متكرر؟"),
        choices=[("True", _("نعم")), ("False", _("لا"))],
        coerce=lambda value: value == "True",
        widget=forms.RadioSelect,
        initial="True",
    )

    class Meta:
        model = Subscription
        fields = [
            "service_name",
            "category",
            "amount",
            "currency",
            "billing_cycle",
            "start_date",
            "next_renewal_date",
            "status",
            "is_recurring",
            "reminder_days_before",
            "notes",
        ]
        widgets = {
            "service_name": forms.TextInput(attrs={"list": "service-names", "autocomplete": "off"}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "inputmode": "decimal"}),
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "next_renewal_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "reminder_days_before": forms.NumberInput(attrs={"min": "0", "max": "60"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("start_date", "next_renewal_date"):
            self.fields[name].input_formats = ["%Y-%m-%d"]
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].choices = Category.display_choices(_("اختر التصنيف"))

    def clean_service_name(self):
        name = self.cleaned_data["service_name"].strip()
        if not name:
            raise forms.ValidationError(_("اسم الخدمة مطلوب."))
        return name

    def clean(self):
        cleaned = super().clean()
        start, renewal = cleaned.get("start_date"), cleaned.get("next_renewal_date")
        if start and renewal and renewal < start:
            self.add_error("next_renewal_date", _("تاريخ التجديد القادم لا يمكن أن يسبق تاريخ البداية."))
        return cleaned


class SubscriptionFilterForm(forms.Form):
    ORDERING = [
        ("renewal", _("التجديد القادم (الأقرب أولًا)")),
        ("-renewal", _("التجديد القادم (الأبعد أولًا)")),
        ("amount", _("المبلغ (الأقل أولًا)")),
        ("-amount", _("المبلغ (الأعلى أولًا)")),
        ("name", _("الاسم (تصاعدي)")),
        ("-name", _("الاسم (تنازلي)")),
    ]
    q = forms.CharField(label=_("بحث باسم الخدمة"), required=False, max_length=100)
    status = forms.ChoiceField(
        label=_("الحالة"),
        required=False,
        choices=[("", _("كل الاشتراكات (عدا المؤرشفة)"))] + list(Subscription.Status.choices),
    )
    category = forms.ModelChoiceField(
        label=_("التصنيف"), queryset=Category.objects.all(), required=False, empty_label=_("كل التصنيفات")
    )
    billing_cycle = forms.ChoiceField(
        label=_("دورة الفوترة"),
        required=False,
        choices=[("", _("كل الدورات"))] + list(Subscription.BillingCycle.choices),
    )
    ordering = forms.ChoiceField(label=_("الترتيب"), required=False, choices=ORDERING)
    review = forms.BooleanField(label=_("تحتاج إلى مراجعة فقط"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = Category.display_choices(_("كل التصنيفات"))
