import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "account_type",
                    models.CharField(
                        choices=[("individual", "فرد"), ("business", "منشأة")],
                        default="individual",
                        max_length=20,
                        verbose_name="نوع الحساب",
                    ),
                ),
                ("business_name", models.CharField(blank=True, max_length=150, verbose_name="اسم المنشأة")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="المستخدم",
                    ),
                ),
            ],
            options={
                "verbose_name": "ملف شخصي",
                "verbose_name_plural": "الملفات الشخصية",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(account_type="individual") | ~models.Q(business_name=""),
                        name="business_requires_business_name",
                        violation_error_message="اسم المنشأة مطلوب لحساب المنشأة.",
                    )
                ],
            },
        ),
    ]
