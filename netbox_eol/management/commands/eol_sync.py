"""`manage.py eol_sync` — run an eol.network lifecycle sync on demand."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from netbox_eol import __version__, sync
from netbox_eol.client import EolClient
from netbox_eol.client.exceptions import EolApiError
from netbox_eol.models import EolSettings

USER_AGENT = f"netbox-eol-plugin/{__version__} (+https://github.com/torresmva/netbox-eol)"


class Command(BaseCommand):
    help = "Run an eol.network lifecycle + KEV sync for matched DeviceTypes."

    def handle(self, *args, **options):
        settings = EolSettings.load()
        api_key = settings.get_api_key()
        if not api_key:
            self.stderr.write(
                self.style.ERROR("No API key configured (set one in plugin settings).")
            )
            return

        client = EolClient(
            base_url=settings.base_url,
            api_key=api_key,
            user_agent=USER_AGENT,
        )

        settings.last_sync_started = timezone.now()
        settings.last_sync_status = "never"
        settings.save()
        try:
            counts = sync.run_sync(client, settings)
        except EolApiError as exc:
            settings.last_sync_status = "failed"
            settings.last_sync_message = f"{type(exc).__name__}: {exc}"
            settings.last_sync_finished = timezone.now()
            settings.save()
            self.stderr.write(self.style.ERROR(f"Sync failed: {exc}"))
            return

        settings.last_sync_status = "success"
        settings.last_sync_message = (
            f"auto={counts['auto']} review={counts['review']} "
            f"unmatched={counts['unmatched']} invalid={counts['invalid']}"
        )
        settings.last_sync_finished = timezone.now()
        settings.save()
        self.stdout.write(self.style.SUCCESS(f"Sync complete: {settings.last_sync_message}"))
