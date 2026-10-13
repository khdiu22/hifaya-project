from django import forms


def date_field(label, required=False):
    """HTML5 date input without JavaScript; always parsed as YYYY-MM-DD."""
    return forms.DateField(
        label=label,
        required=required,
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
