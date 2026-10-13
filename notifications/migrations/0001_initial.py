import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150, verbose_name="العنوان")),
                ("message", models.TextField(verbose_name="الرسالة")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")),
                ("is_read", models.BooleanField(default=False, verbose_name="مقروء")),
                (
                    "subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="subscriptions.subscription",
                        verbose_name="الاشتراك",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="المستخدم",
                    ),
                ),
            ],
            options={
                "verbose_name": "إشعار",
                "verbose_name_plural": "الإشعارات",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ReminderLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("renewal_date", models.DateField(verbose_name="تاريخ التجديد")),
                ("days_before", models.PositiveSmallIntegerField(verbose_name="الأيام قبل التجديد")),
                ("sent_at", models.DateTimeField(auto_now_add=True, verbose_name="وقت الإرسال")),
                ("channel", models.CharField(default="in_app", max_length=20, verbose_name="القناة")),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reminder_logs",
                        to="subscriptions.subscription",
                        verbose_name="الاشتراك",
                    ),
                ),
            ],
            options={
                "verbose_name": "سجل تذكير",
                "verbose_name_plural": "سجلات التذكير",
                "ordering": ["-sent_at", "-id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("subscription", "renewal_date", "days_before"),
                        name="uniq_reminder_per_due_date",
                        violation_error_message="تم إنشاء هذا التذكير مسبقًا.",
                    )
                ],
            },
        ),
    ]
