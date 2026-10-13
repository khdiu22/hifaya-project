from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("read-all/", views.notification_mark_all_read, name="read_all"),
    path("check/", views.check_reminders, name="check"),
    path("<int:pk>/read/", views.notification_mark_read, name="read"),
]
