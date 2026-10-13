from django.utils.translation import gettext_lazy as _
from django import forms

from core.forms import date_field


class NotificationFilterForm(forms.Form):
    state = forms.ChoiceField(
        label=_("حالة القراءة"),
        required=False,
        choices=[("", _("الكل")), ("unread", _("غير المقروءة")), ("read", _("المقروءة"))],
    )
    date_from = date_field(_("من تاريخ"))
    date_to = date_field(_("إلى تاريخ"))

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("date_from"), cleaned.get("date_to")
        if start and end and start > end:
            self.add_error("date_to", _("تاريخ النهاية يجب ألا يسبق تاريخ البداية."))
        return cleaned
