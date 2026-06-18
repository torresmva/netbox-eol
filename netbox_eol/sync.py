"""Sync orchestration: NetBox DeviceTypes -> eol.network match -> cached tables.

Takes an injected client (the real EolClient or a fake), so the pipeline is
testable without a live API. Pure orchestration over the Django models + the
framework-free matching core.
"""

from datetime import date, datetime, timezone

from django.utils import timezone as django_timezone

from dcim.models import DeviceType

from netbox_eol import __version__, matching
from netbox_eol.client import EolClient
from netbox_eol.client.exceptions import EolApiError
from netbox_eol.models import DeviceTypeMapping, LifecycleProduct, ManufacturerVendorMap

DEFAULT_USER_AGENT = f"netbox-eol-plugin/{__version__} (+https://github.com/torresmva/netbox-eol)"


def _parse_date(value):
    return date.fromisoformat(value) if value else None


def _parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _vendor_hint(device_type):
    mapping = ManufacturerVendorMap.objects.filter(manufacturer=device_type.manufacturer).first()
    if mapping:
        return mapping.vendor_slug
    return device_type.manufacturer.slug


def target_device_types(targets):
    qs = DeviceType.objects.select_related("manufacturer")
    if targets == "in_use":
        qs = qs.filter(instances__isnull=False).distinct()
    return qs


def _upsert_product(record, now):
    kev = record.kev
    product, _ = LifecycleProduct.objects.update_or_create(
        vendor_slug=record.vendor_slug,
        product_id=record.product_id,
        defaults=dict(
            product_name=record.product_name or "",
            product_type=record.product_type or "",
            applicable_series=record.applicable_series or [],
            series_slug=record.series_slug or "",
            category=record.category or "",
            lifecycle_status=record.lifecycle_status or "",
            announcement_date=_parse_date(record.announcement_date),
            end_of_sale_date=_parse_date(record.end_of_sale_date),
            last_date_of_support=_parse_date(record.last_date_of_support),
            end_of_sw_maintenance_date=_parse_date(record.end_of_sw_maintenance_date),
            end_of_vuln_security_support_date=_parse_date(record.end_of_vuln_security_support_date),
            end_of_routine_failure_analysis_date=_parse_date(
                record.end_of_routine_failure_analysis_date
            ),
            replacement_product=record.replacement_product or "",
            url=record.url or "",
            kev_exposed=kev.exposed if kev else False,
            kev_count=kev.count if kev else 0,
            kev_cve_ids=kev.cve_ids if kev else [],
            kev_catalog_version=(kev.catalog_version or "") if kev else "",
            kev_updated_at=_parse_dt(kev.updated_at) if kev else None,
            raw=record.raw or {},
            fetched_at=now,
        ),
    )
    return product


def _learn_vendor(device_type, vendor_slug):
    if not vendor_slug:
        return
    existing = ManufacturerVendorMap.objects.filter(manufacturer=device_type.manufacturer).first()
    if existing and existing.source == "manual":
        return  # never overwrite an admin-set mapping
    ManufacturerVendorMap.objects.update_or_create(
        manufacturer=device_type.manufacturer,
        defaults={"vendor_slug": vendor_slug, "source": "learned"},
    )


def run_sync(client, settings, now=None):
    """Match all target DeviceTypes, upsert products/mappings, refresh KEV.

    Returns a counts dict: matched / review / unmatched / invalid.
    """
    now = now or datetime.now(timezone.utc)

    queries, by_ref = [], {}
    for device_type in target_device_types(settings.sync_targets):
        query = matching.build_query(
            ref=device_type.pk,
            model=device_type.model,
            part_number=device_type.part_number,
            vendor_slug=_vendor_hint(device_type),
        )
        if query:
            queries.append(query)
            by_ref[str(device_type.pk)] = device_type

    counts = {"auto": 0, "review": 0, "unmatched": 0, "invalid": 0}
    for row in client.match(queries) if queries else []:
        device_type = by_ref.get(str(row.ref))
        if device_type is None:
            continue
        action = matching.classify(row, settings.auto_accept_tiers, settings.review_tiers)
        counts[action] = counts.get(action, 0) + 1
        _learn_vendor(device_type, matching.learned_vendor(row))

        mapping, _ = DeviceTypeMapping.objects.get_or_create(device_type=device_type)
        if mapping.is_overridden:
            continue  # protect manual overrides from auto-sync

        mapping.match_query = row.query or ""
        mapping.vendor_resolved = row.vendor_resolved or ""
        mapping.match_confidence = row.confidence
        mapping.last_matched_at = now
        if action == "auto" and row.match:
            mapping.product = _upsert_product(row.match, now)
            mapping.match_method = "auto"
        else:
            mapping.product = None
            mapping.match_method = "none"
        mapping.save()

    _refresh_kev(client, now)
    return counts


def run_and_record(settings, user_agent=DEFAULT_USER_AGENT):
    """Build a client from settings, run the sync, and record last_sync_* status.

    Shared by the management command, the scheduled job, and the "Sync now" action.
    Returns the counts dict; re-raises after recording a failure.
    """
    api_key = settings.get_api_key()
    if not api_key:
        settings.last_sync_status = "failed"
        settings.last_sync_message = "No API key configured."
        settings.last_sync_finished = django_timezone.now()
        settings.save()
        raise EolApiError("No API key configured.")

    client = EolClient(base_url=settings.base_url, api_key=api_key, user_agent=user_agent)
    settings.last_sync_started = django_timezone.now()
    settings.save()
    try:
        counts = run_sync(client, settings)
    except Exception as exc:
        settings.last_sync_status = "failed"
        settings.last_sync_message = f"{type(exc).__name__}: {exc}"
        settings.last_sync_finished = django_timezone.now()
        settings.save()
        raise
    settings.last_sync_status = "success"
    settings.last_sync_message = (
        f"auto={counts['auto']} review={counts['review']} "
        f"unmatched={counts['unmatched']} invalid={counts['invalid']}"
    )
    settings.last_sync_finished = django_timezone.now()
    settings.save()
    return counts


def _refresh_kev(client, now):
    products = {
        (m.product.vendor_slug, m.product.product_id): m.product
        for m in DeviceTypeMapping.objects.filter(product__isnull=False).select_related("product")
    }
    if not products:
        return
    lookups = [{"vendor_slug": v, "product_id": p} for (v, p) in products]
    for result in client.kev_lookup(lookups):
        if not result.found or result.kev is None:
            continue
        product = products.get((result.vendor_slug, result.product_id))
        if product is None:
            continue
        product.kev_exposed = result.kev.exposed
        product.kev_count = result.kev.count
        product.kev_cve_ids = result.kev.cve_ids
        product.kev_catalog_version = result.kev.catalog_version or ""
        product.kev_updated_at = _parse_dt(result.kev.updated_at)
        product.save()
