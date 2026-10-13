import decimal

import django.core.validators
import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80, verbose_name="اسم التصنيف")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="الوصف")),
            ],
            options={
                "verbose_name": "تصنيف",
                "verbose_name_plural": "التصنيفات",
                "ordering": ["name"],
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("name"),
                        name="uniq_category_name_ci",
                        violation_error_message="يوجد تصنيف بنفس الاسم.",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("service_name", models.CharField(max_length=120, verbose_name="اسم الخدمة")),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(
                                decimal.Decimal("0"), message="لا يمكن أن يكون المبلغ سالبًا."
                            )
                        ],
                        verbose_name="المبلغ",
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        choices=[
                            ("SAR", "ريال سعودي (SAR)"),
                            ("USD", "دولار أمريكي (USD)"),
                            ("EUR", "يورو (EUR)"),
                            ("GBP", "جنيه إسترليني (GBP)"),
                            ("AED", "درهم إماراتي (AED)"),
                        ],
                        default="SAR",
                        max_length=3,
                        verbose_name="العملة",
                    ),
                ),
                (
                    "billing_cycle",
                    models.CharField(
                        choices=[
                            ("weekly", "أسبوعية"),
                            ("monthly", "شهرية"),
                            ("quarterly", "ربع سنوية"),
                            ("yearly", "سنوية"),
                        ],
                        default="monthly",
                        max_length=10,
                        verbose_name="دورة الفوترة",
                    ),
                ),
                ("start_date", models.DateField(verbose_name="تاريخ البداية")),
                ("next_renewal_date", models.DateField(verbose_name="تاريخ التجديد القادم")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "نشط"),
                            ("paused", "متوقف"),
                            ("cancelled", "ملغى"),
                            ("archived", "مؤرشف"),
                        ],
                        default="active",
                        max_length=10,
                        verbose_name="الحالة",
                    ),
                ),
                ("is_recurring", models.BooleanField(default=True, verbose_name="متكرر؟")),
                (
                    "reminder_days_before",
                    models.PositiveSmallIntegerField(
                        default=3,
                        validators=[
                            django.core.validators.MaxValueValidator(60, message="الحد الأقصى للتذكير 60 يومًا.")
                        ],
                        verbose_name="التذكير قبل التجديد (بالأيام)",
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="ملاحظات")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name="subscriptions",
                        to="subscriptions.category",
                        verbose_name="التصنيف",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscriptions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="المستخدم",
                    ),
                ),
            ],
            options={
                "verbose_name": "اشتراك",
                "verbose_name_plural": "الاشتراكات",
                "ordering": ["next_renewal_date", "service_name"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(amount__gte=0),
                        name="subscription_amount_non_negative",
                        violation_error_message="لا يمكن أن يكون المبلغ سالبًا.",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(next_renewal_date__gte=models.F("start_date")),
                        name="subscription_renewal_not_before_start",
                        violation_error_message="تاريخ التجديد القادم لا يمكن أن يسبق تاريخ البداية.",
                    ),
                ],
            },
        ),
    ]
