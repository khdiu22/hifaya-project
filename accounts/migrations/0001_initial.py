
# استيراد أداة الحذف الخاصة بالعلاقات بين الجداول من Django
import django.db.models.deletion

# استيراد إعدادات المشروع للوصول إلى موديل المستخدم المعتمد في المشروع
from django.conf import settings

# استيراد أدوات إنشاء الترحيلات والحقول والموديلات
from django.db import migrations, models


# كلاس يمثل عملية ترحيل قاعدة البيانات (Migration)
class Migration(migrations.Migration):

    # تحديد أن هذا هو الترحيل الأول لإنشاء الموديل
    initial = True

    # تحديد الترحيلات التي يجب تنفيذها قبل هذا الترحيل
    dependencies = [
        # التأكد من أن موديل المستخدم موجود قبل إنشاء العلاقة معه
        # AUTH_USER_MODEL يسمح باستخدام موديل المستخدم المحدد في إعدادات المشروع
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    # العمليات التي سينفذها Django على قاعدة البيانات
    operations = [

        # إنشاء جدول جديد باسم Profile
        migrations.CreateModel(
            name="Profile",

            # تحديد الحقول التي سيحتوي عليها الجدول
            fields=[

                # المفتاح الأساسي للجدول، ويُنشأ تلقائيًا
                # BigAutoField يولّد رقمًا متزايدًا لكل سجل
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),

                # تحديد نوع الحساب: فرد أو منشأة
                # القيمة الافتراضية هي individual، أي فرد
                (
                    "account_type",
                    models.CharField(
                        choices=[
                            ("individual", "فرد"),
                            ("business", "منشأة"),
                        ],
                        default="individual",
                        max_length=20,
                        verbose_name="نوع الحساب",
                    ),
                ),

                # اسم المنشأة، وهو اختياري على مستوى الحقل
                # blank=True يسمح بتركه فارغًا في النماذج والتحقق منها
                (
                    "business_name",
                    models.CharField(
                        blank=True,
                        max_length=150,
                        verbose_name="اسم المنشأة",
                    ),
                ),

                # حفظ تاريخ ووقت إنشاء الملف الشخصي تلقائيًا
                # auto_now_add=True يحدد القيمة عند إنشاء السجل أول مرة
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="تاريخ الإنشاء",
                    ),
                ),

                # تحديث تاريخ ووقت آخر تعديل تلقائيًا عند حفظ السجل
                # auto_now=True يحدّث القيمة عند الحفظ
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name="آخر تحديث",
                    ),
                ),

                # ربط الملف الشخصي بمستخدم واحد
                (
                    "user",
                    models.OneToOneField(
                        # إذا حُذف المستخدم، يُحذف ملفه الشخصي المرتبط به
                        on_delete=django.db.models.deletion.CASCADE,

                        # يسمح بالوصول إلى الملف الشخصي من خلال user.profile
                        related_name="profile",

                        # تحديد موديل المستخدم المعتمد في إعدادات المشروع
                        to=settings.AUTH_USER_MODEL,

                        # الاسم الظاهر للحقل في واجهات Django
                        verbose_name="المستخدم",
                    ),
                ),
            ],

            # إعدادات إضافية للموديل والجدول
            options={

                # الاسم المفرد الذي يظهر في واجهات Django
                "verbose_name": "ملف شخصي",

                # الاسم الجمع الذي يظهر في واجهات Django
                "verbose_name_plural": "الملفات الشخصية",

                # القيود التي يجب أن تلتزم بها البيانات في قاعدة البيانات
                "constraints": [

                    # التحقق من أن حساب المنشأة يحتوي على اسم منشأة
                    models.CheckConstraint(
                        # الشرط يسمح بالحساب الفردي دائمًا،
                        # أو بحساب المنشأة إذا كان اسم المنشأة غير فارغ
                        condition=(
                            models.Q(account_type="individual")
                            | ~models.Q(business_name="")
                        ),

                        # اسم مميز للقيد داخل قاعدة البيانات
                        name="business_requires_business_name",

                        # رسالة الخطأ عند مخالفة القيد
                        violation_error_message="اسم المنشأة مطلوب لحساب المنشأة.",
                    )
                ],
            },
        ),
    ]
