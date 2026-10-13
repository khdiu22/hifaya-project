from django.utils.translation import gettext_lazy as _
from django import forms

from core.forms import date_field
from subscriptions.models import Category, Subscription


class ReportFilterForm(forms.Form):
    date_from = date_field(_("من تاريخ"))
    date_to = date_field(_("إلى تاريخ"))
    status = forms.ChoiceField(
        label=_("حالة الاشتراك"), required=False, choices=[("", _("كل الحالات"))] + list(Subscription.Status.choices)
    )
    category = forms.ModelChoiceField(
        label=_("التصنيف"), queryset=Category.objects.all(), required=False, empty_label=_("كل التصنيفات")
    )
    subscription = forms.ModelChoiceField(
        label=_("الاشتراك"), queryset=Subscription.objects.none(), required=False, empty_label=_("كل الاشتراكات")
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subscription"].queryset = Subscription.objects.filter(user=user).order_by("service_name")
        self.fields["category"].choices = Category.display_choices(_("كل التصنيفات"))

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("date_from"), cleaned.get("date_to")
        if start and end and start > end:
            self.add_error("date_to", _("تاريخ النهاية يجب ألا يسبق تاريخ البداية."))
        return cleaned
