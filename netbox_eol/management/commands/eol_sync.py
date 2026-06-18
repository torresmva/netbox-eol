"""`manage.py eol_sync` — run an eol.network lifecycle sync on demand."""

from django.core.management.base import BaseCommand

from netbox_eol import sync
from netbox_eol.client.exceptions import EolApiError
from netbox_eol.models import EolSettings


class Command(BaseCommand):
    help = "Run an eol.network lifecycle + KEV sync for matched DeviceTypes."

    def handle(self, *args, **options):
        settings = EolSettings.load()
        try:
            sync.run_and_record(settings)
        except EolApiError as exc:
            self.stderr.write(self.style.ERROR(f"Sync failed: {exc}"))
            return
        self.stdout.write(self.style.SUCCESS(f"Sync complete: {settings.last_sync_message}"))
