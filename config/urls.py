
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("accounts.urls")),
    path("subscriptions/", include("subscriptions.urls")),
    path("payments/", include("payments.urls")),
    path("notifications/", include("notifications.urls")),
    path("reports/", include("reports.urls")),

    # Serve static files locally when DEBUG is False
    path(
        "static/<path:path>",
        serve,
        {"document_root": settings.BASE_DIR / "static"},
    ),

    path("", include("core.urls")),
]

# Serve uploaded media files during development only
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
