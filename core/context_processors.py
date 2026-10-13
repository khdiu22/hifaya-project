from .theme import THEME_COOKIE, THEMES


def theme(request):
    """Expose the current theme (session -> cookie -> light)."""
    current = request.session.get("theme") or request.COOKIES.get(THEME_COOKIE)
    if current not in THEMES:
        current = "light"
    return {"theme": current, "next_theme": "dark" if current == "light" else "light"}


def unread_notifications(request):
    """Unread notification count for the sidebar badge."""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from notifications.models import Notification

        return {"unread_count": Notification.objects.filter(user=user, is_read=False).count()}
    return {"unread_count": 0}
