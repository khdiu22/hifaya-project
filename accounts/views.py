from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm
from .models import Profile


def saved_language(user):
    """The language saved in the user's profile ('ar' or 'en'), or None if there is none."""
    profile = getattr(user, "profile", None)
    language = getattr(profile, "preferred_language", None)
    return language if language in dict(settings.LANGUAGES) else None


def set_language_cookie(response, language):
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )


class HifayaLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember_me"):
            # "Remember me" unchecked -> the session cookie ends when the browser closes.
            self.request.session.set_expiry(0)
        # Use the language saved in the account (falls back to the language chosen on the login page).
        language = saved_language(self.request.user) or translation.get_language()
        set_language_cookie(response, language)
        with translation.override(language):
            welcome = str(_("👋 أهلًا بعودتك إلى حفاية!"))
        messages.success(self.request, welcome)
        return response


def register(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("🎉 تم إنشاء حسابك بنجاح! سجّل دخولك للبدء."))
            return redirect("accounts:login")
        messages.error(request, _("❌ تعذّر إنشاء الحساب، راجع الحقول المظللة."))
    else:
        form = RegisterForm(initial={"account_type": "individual"})
    return render(request, "accounts/register.html", {"form": form})


@require_POST
def save_language_preference(request):
    """Language button. Works for visitors (cookie) and for signed-in users (cookie + saved in their profile)."""
    language = request.POST.get("language", "")
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = "/"
    response = redirect(next_url)
    if language not in dict(settings.LANGUAGES):
        return response
    if request.user.is_authenticated:
        profile, _created = Profile.objects.get_or_create(user=request.user)
        if profile.preferred_language != language:
            profile.preferred_language = language
            profile.save(update_fields=["preferred_language"])
    set_language_cookie(response, language)
    return response
