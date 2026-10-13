from django.db import migrations

DEFAULT_CATEGORIES = [
    ("الترفيه والموسيقى", "منصات المشاهدة والموسيقى"),
    ("الذكاء الاصطناعي", "أدوات وخدمات الذكاء الاصطناعي"),
    ("التخزين والإنتاجية", "التخزين السحابي وأدوات العمل"),
    ("التصميم والأدوات", "التصميم والبرمجة والأدوات"),
    ("التسوق والخدمات الرقمية", "العضويات والخدمات الرقمية"),
    ("الألعاب", "اشتراكات الألعاب"),
    ("التعليم", "التعلم والدورات"),
    ("أخرى", "أي اشتراك لا يناسب بقية التصنيفات"),
]


def add_categories(apps, schema_editor):
    Category = apps.get_model("subscriptions", "Category")
    for name, description in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(name=name, defaults={"description": description})


def remove_categories(apps, schema_editor):
    Category = apps.get_model("subscriptions", "Category")
    Category.objects.filter(name__in=[name for name, _ in DEFAULT_CATEGORIES], subscriptions__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]
    operations = [migrations.RunPython(add_categories, remove_categories)]
