from datetime import date

from django.core.management.base import BaseCommand, CommandError

from notifications.services import send_due_reminders


class Command(BaseCommand):
    help = (
        "Create due renewal reminders (in-app + email when SMTP is configured). "
        "Run it daily with cron / Task Scheduler; it does NOT schedule itself."
    )

    def add_arguments(self, parser):
        parser.add_argument("--today", help="Simulate another date (YYYY-MM-DD), useful for demos.")

    def handle(self, *args, **options):
        today = None
        if options.get("today"):
            try:
                today = date.fromisoformat(options["today"])
            except ValueError as exc:
                raise CommandError("--today must look like 2026-10-31") from exc
        result = send_due_reminders(today=today)
        self.stdout.write(
            self.style.SUCCESS(
                f"Reminders created: {result.created} | duplicates skipped: {result.skipped_duplicates} | emails sent: {result.emails_sent}"
            )
        )
