from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send one test e-mail to check the e-mail settings: python manage.py send_test_email you@example.com"

    def add_arguments(self, parser):
        parser.add_argument("to", help="Recipient e-mail address")

    def handle(self, *args, **options):
        try:
            sent = send_mail(
                "Hifaya test e-mail",
                "If you can read this message, e-mail sending works.",
                settings.DEFAULT_FROM_EMAIL,
                [options["to"]],
                fail_silently=False,
            )
        except Exception as exc:  # noqa: BLE001 - show the real reason to the user
            raise CommandError(f"Could not send the e-mail: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} e-mail using {settings.EMAIL_BACKEND}"))
