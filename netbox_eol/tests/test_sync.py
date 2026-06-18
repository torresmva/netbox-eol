"""NetBox framework tests for the sync orchestration (with a fake client)."""

from django.test import TestCase
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site

from netbox_eol import sync
from netbox_eol.client.models import KevLookupResult, MatchRow
from netbox_eol.models import (
    DeviceTypeMapping,
    EolSettings,
    LifecycleProduct,
    ManufacturerVendorMap,
)


class FakeClient:
    def __init__(self, rows=(), kev=()):
        self._rows = list(rows)
        self._kev = list(kev)
        self.match_calls = []
        self.kev_calls = []

    def match(self, queries):
        self.match_calls.append(queries)
        return self._rows

    def kev_lookup(self, products):
        self.kev_calls.append(products)
        return self._kev


def _row(ref, **kw):
    base = {
        "ref": str(ref),
        "query": "Q",
        "vendor": None,
        "vendor_resolved": None,
        "matched": False,
        "confidence": "none",
        "match": None,
    }
    base.update(kw)
    return MatchRow.from_dict(base)


class RunSyncTest(TestCase):
    def setUp(self):
        self.settings = EolSettings.load()
        self.mfg = Manufacturer.objects.create(name="Cisco", slug="cisco")
        self.dt = DeviceType.objects.create(
            manufacturer=self.mfg, model="C3850", slug="c3850", part_number="WS-C3850-48T"
        )
        site = Site.objects.create(name="S", slug="s")
        role = DeviceRole.objects.create(name="R", slug="r", color="ffffff")
        Device.objects.create(name="d", device_type=self.dt, role=role, site=site)

    def test_query_uses_part_number_and_manufacturer_slug_hint(self):
        client = FakeClient()
        sync.run_sync(client, self.settings)
        sent = client.match_calls[0][0]
        self.assertEqual(sent["q"], "WS-C3850-48T")
        self.assertEqual(sent["vendor"], "cisco")

    def test_auto_match_upserts_product_mapping_and_learns_vendor(self):
        match = {
            "vendor_slug": "cisco",
            "product_id": "WS-C3850-48T",
            "product_name": "Catalyst 3850",
            "lifecycle_status": "end_of_life",
            "last_date_of_support": "2022-10-30",
            "kev": {"exposed": True, "count": 1, "cve_ids": ["CVE-2023-20198"]},
        }
        row = _row(
            self.dt.pk, vendor_resolved="cisco", matched=True, confidence="exact", match=match
        )
        kev = [
            KevLookupResult.from_dict(
                {
                    "vendor_slug": "cisco",
                    "product_id": "WS-C3850-48T",
                    "found": True,
                    "kev": {"exposed": True, "count": 1, "cve_ids": ["CVE-2023-20198"]},
                }
            )
        ]
        counts = sync.run_sync(FakeClient([row], kev), self.settings)

        self.assertEqual(counts["auto"], 1)
        product = LifecycleProduct.objects.get(vendor_slug="cisco", product_id="WS-C3850-48T")
        self.assertEqual(product.lifecycle_status, "end_of_life")
        self.assertTrue(product.kev_exposed)
        mapping = DeviceTypeMapping.objects.get(device_type=self.dt)
        self.assertEqual(mapping.product, product)
        self.assertEqual(mapping.match_method, "auto")
        self.assertEqual(mapping.match_confidence, "exact")
        self.assertTrue(
            ManufacturerVendorMap.objects.filter(
                manufacturer=self.mfg, vendor_slug="cisco"
            ).exists()
        )

    def test_review_tier_does_not_attach_product(self):
        row = _row(
            self.dt.pk,
            matched=True,
            confidence="family",
            match={"vendor_slug": "x", "product_id": "y"},
        )
        counts = sync.run_sync(FakeClient([row]), self.settings)
        self.assertEqual(counts["review"], 1)
        mapping = DeviceTypeMapping.objects.get(device_type=self.dt)
        self.assertEqual(mapping.match_method, "none")
        self.assertEqual(mapping.match_confidence, "family")
        self.assertIsNone(mapping.product)

    def test_override_is_protected_from_sync(self):
        DeviceTypeMapping.objects.create(
            device_type=self.dt, is_overridden=True, match_method="manual"
        )
        row = _row(
            self.dt.pk,
            matched=True,
            confidence="exact",
            match={"vendor_slug": "x", "product_id": "y"},
        )
        sync.run_sync(FakeClient([row]), self.settings)
        mapping = DeviceTypeMapping.objects.get(device_type=self.dt)
        self.assertEqual(mapping.match_method, "manual")
        self.assertIsNone(mapping.product)
