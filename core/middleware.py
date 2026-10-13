from django.conf import settings
from django.utils import translation


class UserLanguageMiddleware:
    """Signed-in users see the language saved in their profile, on any browser or device."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, "profile", None)
            language = getattr(profile, "preferred_language", None)
            if language in dict(settings.LANGUAGES):
                translation.activate(language)
                request.LANGUAGE_CODE = translation.get_language()
        return self.get_response(request)


class ResetLanguageMiddleware:
    """After every request, put the thread back to the default language.

    Without this, the language of one request (for example English) can stay active in the same
    thread and leak into the next code that runs there (tests, background work).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        finally:
            translation.deactivate()
