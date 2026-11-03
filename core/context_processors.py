
# استيراد اسم ملف تعريف الارتباط الخاص بالثيم
# واستيراد قائمة الثيمات المسموح باستخدامها في المشروع
from .theme import THEME_COOKIE, THEMES


# ==========================================
# معالج إعدادات المظهر (Theme Context Processor)
# ==========================================

# هذه الدالة تسمح لقوالب HTML بالوصول إلى بيانات الثيم
# يجب تسجيلها في TEMPLATES داخل ملف settings.py
def theme(request):
    """Expose the current theme (session -> cookie -> light)."""

    # محاولة الحصول على الثيم المحفوظ في جلسة المستخدم أولًا
    # إذا لم توجد قيمة في الجلسة، تتم قراءة الثيم من ملف تعريف الارتباط
    # request.COOKIES يحتوي على ملفات تعريف الارتباط المرسلة من المتصفح
    current = (
        request.session.get("theme")
        or request.COOKIES.get(THEME_COOKIE)
    )

    # التحقق من أن الثيم المختار موجود ضمن الثيمات المسموح بها
    # إذا كانت القيمة مفقودة أو غير صالحة، يتم استخدام الثيم الفاتح
    if current not in THEMES:
        current = "light"

    # إرجاع قاموس يحتوي على البيانات التي ستصبح متاحة داخل القوالب
    return {
        # الثيم الحالي، ويمكن استخدامه في HTML لتحديد المظهر
        "theme": current,

        # تحديد الثيم المعاكس للثيم الحالي
        # إذا كان الحالي فاتحًا، يكون التالي داكنًا، والعكس صحيح
        "next_theme": "dark" if current == "light" else "light",
    }


# ==========================================
# عدد الإشعارات غير المقروءة
# (Unread Notifications)
# ==========================================

# هذه الدالة توفر عدد الإشعارات غير المقروءة للقوالب
# يمكن استخدام العدد لعرض شارة بجانب أيقونة الإشعارات في القائمة الجانبية
def unread_notifications(request):
    """Unread notification count for the sidebar badge."""

    # الحصول على المستخدم من الطلب
    # getattr تسمح بإرجاع None إذا لم تكن الخاصية user موجودة
    user = getattr(request, "user", None)

    # التحقق من وجود مستخدم وأنه مسجل الدخول
    if user is not None and user.is_authenticated:

        # استيراد نموذج الإشعارات عند الحاجة إلى استخدامه
        # الاستيراد هنا محلي داخل الدالة بدلًا من أعلى الملف
        from notifications.models import Notification

        # البحث عن الإشعارات التابعة للمستخدم الحالي فقط
        # is_read=False يعني أن الإشعار لم تتم قراءته
        # count() يحسب عدد الإشعارات المطابقة دون الحاجة إلى جلبها كلها
        return {
            "unread_count": Notification.objects.filter(
                user=user,
                is_read=False,
            ).count()
        }

    # إذا لم يكن المستخدم مسجل الدخول، يكون العدد صفرًا
    return {"unread_count": 0}
