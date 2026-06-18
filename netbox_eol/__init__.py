"""netbox_eol — NetBox plugin enriching DeviceType/Device inventory with
eol.network lifecycle + CISA KEV data.

The PluginConfig needs NetBox (``netbox.plugins``). That import is GUARDED so the
framework-free API client (``netbox_eol.client``) stays importable and
unit-testable without a NetBox/Django install. Inside a real NetBox the guard is a
no-op and ``config`` is exported for plugin discovery.
"""
__version__ = "0.1.0"

try:
    from netbox.plugins import PluginConfig
except ModuleNotFoundError:  # NetBox absent (e.g. running the client's unit tests)
    PluginConfig = None


if PluginConfig is not None:

    class EolNetworkConfig(PluginConfig):
        name = "netbox_eol"
        verbose_name = "eol.network Lifecycle"
        description = (
            "Enrich DeviceType/Device inventory with eol.network hardware "
            "lifecycle and CISA KEV exposure data."
        )
        version = __version__
        author = "Mike Torres"
        base_url = "eol"
        # Researched floor: 4.2 is where @system_job() (recurring system jobs)
        # landed; every other API we use is stable at/before 4.2. Bump max_version
        # per tested release — NetBox is tick-tock (breaking) from 4.4, no LTS.
        min_version = "4.2.0"
        max_version = "4.5.99"
        required_settings = []
        default_settings = {
            "base_url": "https://eol.network/api/v1/",
            "sync_interval_hours": 24,
            "auto_accept_tiers": ["exact"],
            "review_tiers": ["prefix", "family"],
            "sync_targets": "in_use",
            "request_timeout": 10,
            "user_agent": f"netbox-eol-plugin/{__version__} (+https://github.com/mvt410/netbox-eol)",
        }

    config = EolNetworkConfig
