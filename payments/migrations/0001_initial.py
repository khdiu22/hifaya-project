import decimal

import django.core.validators
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
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                ("payment_date", models.DateField(verbose_name="تاريخ الدفع")),
                ("payment_method", models.CharField(blank=True, max_length=50, verbose_name="طريقة الدفع")),
                ("reference", models.CharField(blank=True, max_length=100, verbose_name="مرجع العملية")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("paid", "مدفوعة"),
                            ("pending", "قيد الانتظار"),
                            ("failed", "فاشلة"),
                            ("refunded", "مستردة"),
                        ],
                        default="paid",
                        max_length=10,
                        verbose_name="الحالة",
                    ),
                ),
                ("review_required", models.BooleanField(default=False, verbose_name="تحتاج إلى مراجعة")),
                ("review_reason", models.CharField(blank=True, max_length=255, verbose_name="سبب المراجعة")),
                ("notes", models.TextField(blank=True, verbose_name="ملاحظات")),
                ("is_archived", models.BooleanField(default=False, verbose_name="مؤرشفة")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التسجيل")),
                (
                    "subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.RESTRICT,
                        related_name="payments",
                        to="subscriptions.subscription",
                        verbose_name="الاشتراك المرتبط",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="المستخدم",
                    ),
                ),
            ],
            options={
                "verbose_name": "دفعة",
                "verbose_name_plural": "المدفوعات",
                "ordering": ["-payment_date", "-id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(amount__gte=0),
                        name="payment_amount_non_negative",
                        violation_error_message="لا يمكن أن يكون المبلغ سالبًا.",
                    )
                ],
            },
        ),
    ]
