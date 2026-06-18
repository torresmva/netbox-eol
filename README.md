# netbox-eol

A NetBox plugin that enriches your DeviceType/Device inventory with hardware
**lifecycle** data (announcement / end-of-sale / last-date-of-support / lifecycle
status / recommended replacement) and **CISA KEV** exposure, sourced from the
[eol.network](https://eol.network) API.

It matches each NetBox **DeviceType** to an eol.network product, caches the result
in its own tables, and rolls the status up to every Device of that type. **All UI
reads from the local cache** and never blocks on the API; data is refreshed by a
scheduled background job and an on-demand "Sync now" action.

## Status

Early development. The eol.network API client layer is implemented and tested;
NetBox models, sync job, and UI are in progress.

## Requirements

| | |
|---|---|
| **NetBox** | **4.2+** (`min_version = 4.2.0`) |
| **Python** | 3.10+ |

The 4.2 floor is the version where the `@system_job()` recurring-system-job API
landed (the scheduled sync depends on it); every other plugin API used is stable
at or before 4.2.

## Installation (outline)

```bash
pip install netbox-eol
```

Then add to your NetBox `PLUGINS` and configure:

```python
PLUGINS = ["netbox_eol"]

PLUGINS_CONFIG = {
    "netbox_eol": {
        # Optional bootstrap; the key is normally set in the UI (masked, encrypted).
        # It must be an eol.network *integration* key (self-generated in the portal).
        # "api_key": "...",
        "sync_interval_hours": 24,
        "auto_accept_tiers": ["exact"],
        "sync_targets": "in_use",
    },
}
```

Run migrations (`./manage.py migrate`), generate an **integration key** in the
eol.network portal, paste it into the plugin's settings page, then "Sync now".

## Development

To work on the plugin, install it editable into a NetBox 4.2+ instance
(`pip install -e .`) and add `netbox_eol` to `PLUGINS`. The NetBox framework tests
run in CI against NetBox 4.2.

The API **client** (`netbox_eol/client/`) is deliberately framework-free (no Django)
and unit-tested in isolation — no NetBox required:

```bash
pip install -e ".[test]"
pytest
```

## License

Apache-2.0.
