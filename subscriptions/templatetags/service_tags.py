"""Service icons without JavaScript.

If an official logo file exists in static/img/services/<key>.svg|png it is used;
otherwise a coloured badge with a short label is drawn. Any service that is not
in the list gets the globe icon in light purple.
"""
import re

from django import template
from django.utils.translation import gettext as _
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

register = template.Library()

# key -> (display name, badge label, colour)
SERVICES = {
    "netflix": ("Netflix", "N", "#E50914"),
    "spotify": ("Spotify", "S", "#1DB954"),
    "shahid": ("Shahid", "ش", "#00A86B"),
    "youtubepremium": ("YouTube Premium", "▶", "#FF0000"),
    "disney": ("Disney+", "D+", "#113CCF"),
    "amazonprimevideo": ("Amazon Prime Video", "pv", "#00A8E1"),
    "anghami": ("Anghami", "A", "#7B2FF2"),
    "appletv": ("Apple TV+", "tv", "#1D1D1F"),
    "chatgpt": ("ChatGPT", "G", "#10A37F"),
    "claude": ("Claude", "C", "#D97757"),
    "gemini": ("Gemini", "G", "#4285F4"),
    "perplexity": ("Perplexity", "P", "#20808D"),
    "microsoftcopilot": ("Microsoft Copilot", "Co", "#0F6CBD"),
    "icloud": ("iCloud", "☁", "#3693F3"),
    "googleone": ("Google One", "1", "#4285F4"),
    "microsoft365": ("Microsoft 365", "M", "#D83B01"),
    "dropbox": ("Dropbox", "D", "#0061FF"),
    "zoom": ("Zoom", "Z", "#0B5CFF"),
    "notion": ("Notion", "N", "#2B2B2B"),
    "googleworkspace": ("Google Workspace", "W", "#34A853"),
    "canva": ("Canva", "C", "#00A3AD"),
    "adobecreativecloud": ("Adobe Creative Cloud", "Cc", "#DA1F26"),
    "figma": ("Figma", "F", "#A259FF"),
    "github": ("GitHub", "GH", "#24292F"),
    "jetbrains": ("JetBrains", "JB", "#111111"),
    "amazonprime": ("Amazon Prime", "a", "#FF9900"),
    "playstationplus": ("PlayStation Plus", "PS", "#003791"),
    "xboxgamepass": ("Xbox Game Pass", "X", "#107C10"),
    "nintendoswitchonline": ("Nintendo Switch Online", "N", "#E60012"),
    "duolingosuper": ("Duolingo Super", "D", "#58CC02"),
}

# Arabic spellings that map to the same service keys.
ALIASES = {
    "نتفلكس": "netflix",
    "سبوتيفاي": "spotify",
    "شاهد": "shahid",
    "انغامي": "anghami",
    "أنغامي": "anghami",
    "ديزني": "disney",
    "كلود": "claude",
    "جيميني": "gemini",
    "زوم": "zoom",
    "كانفا": "canva",
    "فيجما": "figma",
    "جيتهب": "github",
}


def normalize(name):
    return re.sub(r"[^a-z0-9\u0600-\u06FF]", "", (name or "").lower())


def lookup(name):
    key = normalize(name)
    key = ALIASES.get(key, key)
    return key if key in SERVICES else None


@register.simple_tag
def service_icon(name):
    key = lookup(name)
    if key is None:
        return format_html('<span class="svc-icon svc-globe" title="{}" aria-hidden="true">🌐</span>', _("خدمة مخصصة"))
    for ext in ("svg", "png"):
        relative = f"img/services/{key}.{ext}"
        if finders.find(relative):
            return format_html('<img class="svc-icon svc-img" src="{}" alt="" width="36" height="36">', static(relative))
    display, label, colour = SERVICES[key]
    return format_html(
        '<span class="svc-icon" style="--svc:{}" title="{}" aria-hidden="true">{}</span>', colour, display, label
    )


@register.simple_tag
def service_options():
    """<option> list for the <datalist> (suggestions without JavaScript)."""
    return format_html_join("", '<option value="{}">', ((v[0],) for v in SERVICES.values()))
