from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("", views.payment_list, name="list"),
    path("add/", views.payment_create, name="create"),
    path("import/", views.payment_import, name="import"),
    path("<int:pk>/", views.payment_detail, name="detail"),
    path("<int:pk>/edit/", views.payment_update, name="update"),
    path("<int:pk>/archive/", views.payment_archive, name="archive"),
    path("<int:pk>/restore/", views.payment_restore, name="restore"),
    path("<int:pk>/reviewed/", views.payment_mark_reviewed, name="reviewed"),
    path("<int:pk>/delete/", views.payment_delete, name="delete"),
]
