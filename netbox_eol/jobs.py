"""Background sync jobs (NetBox JobRunner)."""

from netbox.jobs import JobRunner, system_job

from netbox_eol import sync
from netbox_eol.models import EolSettings


@system_job(interval=1440)  # daily; gated by EolSettings.sync_enabled
class EolSyncJob(JobRunner):
    class Meta:
        name = "EOL Network lifecycle sync"

    def run(self, *args, manual=False, **kwargs):
        settings = EolSettings.load()
        if not manual and not settings.sync_enabled:
            return "Scheduled sync is disabled."
        sync.run_and_record(settings)
        return settings.last_sync_message
