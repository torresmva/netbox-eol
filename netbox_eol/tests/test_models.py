"""NetBox framework tests for the plugin models.

Run by `manage.py test netbox_eol` (needs a NetBox/Django env), not pytest.
"""

from datetime import date

from django.test import TestCase
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site

from netbox_eol.models import (
    DeviceTypeMapping,
    EolSettings,
    LifecycleProduct,
    ManufacturerVendorMap,
)


class EolSettingsTest(TestCase):
    def test_load_returns_singleton(self):
        a = EolSettings.load()
        b = EolSettings.load()
        self.assertEqual(a.pk, 1)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(EolSettings.objects.count(), 1)

    def test_load_sets_default_tiers(self):
        s = EolSettings.load()
        self.assertEqual(s.auto_accept_tiers, ["exact"])
        self.assertEqual(s.review_tiers, ["prefix", "family"])

    def test_save_enforces_single_row(self):
        EolSettings.load()
        other = EolSettings(base_url="https://example.test/")
        other.save()
        self.assertEqual(EolSettings.objects.count(), 1)
        self.assertEqual(EolSettings.objects.get().base_url, "https://example.test/")


class LifecycleProductDateHelpersTest(TestCase):
    def _product(self, **kw):
        return LifecycleProduct(vendor_slug="cisco", product_id="X", **kw)

    def test_is_past_eol_true_when_support_passed(self):
        p = self._product(last_date_of_support=date(2020, 1, 1))
        self.assertTrue(p.is_past_eol(on=date(2026, 1, 1)))

    def test_is_past_eol_false_when_future_or_missing(self):
        future = self._product(last_date_of_support=date(2030, 1, 1))
        self.assertFalse(future.is_past_eol(on=date(2026, 1, 1)))
        self.assertFalse(self._product().is_past_eol(on=date(2026, 1, 1)))

    def test_eol_within_window(self):
        p = self._product(last_date_of_support=date(2026, 3, 1))
        self.assertTrue(p.eol_within(90, on=date(2026, 1, 1)))
        self.assertFalse(p.eol_within(30, on=date(2026, 1, 1)))

    def test_eos_within_window(self):
        p = self._product(end_of_sale_date=date(2026, 2, 1))
        self.assertTrue(p.eos_within(90, on=date(2026, 1, 1)))
        self.assertFalse(p.eos_within(10, on=date(2026, 1, 1)))


class RollupTest(TestCase):
    def test_device_resolves_to_product_via_devicetype_mapping(self):
        mfg = Manufacturer.objects.create(name="Cisco", slug="cisco")
        dt = DeviceType.objects.create(manufacturer=mfg, model="C9300", slug="c9300")
        site = Site.objects.create(name="S", slug="s")
        role = DeviceRole.objects.create(name="R", slug="r", color="ffffff")
        dev = Device.objects.create(name="d1", device_type=dt, role=role, site=site)
        product = LifecycleProduct.objects.create(
            vendor_slug="cisco", product_id="C9300-48T", lifecycle_status="end_of_life"
        )
        DeviceTypeMapping.objects.create(
            device_type=dt, product=product, match_method="auto", match_confidence="exact"
        )

        # rollup traversal: device -> device_type -> eol_mapping -> product
        self.assertEqual(dev.device_type.eol_mapping.product, product)
        self.assertEqual(dev.device_type.eol_mapping.product.lifecycle_status, "end_of_life")

    def test_devicetype_mapping_is_unique_per_device_type(self):
        mfg = Manufacturer.objects.create(name="Cisco", slug="cisco")
        dt = DeviceType.objects.create(manufacturer=mfg, model="C9300", slug="c9300")
        DeviceTypeMapping.objects.create(device_type=dt, match_method="none")
        with self.assertRaises(Exception):
            DeviceTypeMapping.objects.create(device_type=dt, match_method="none")


class ManufacturerVendorMapTest(TestCase):
    def test_maps_manufacturer_to_vendor_slug(self):
        mfg = Manufacturer.objects.create(name="Juniper Networks", slug="juniper-networks")
        m = ManufacturerVendorMap.objects.create(manufacturer=mfg, vendor_slug="juniper")
        self.assertEqual(m.vendor_slug, "juniper")
        self.assertEqual(m.source, "learned")
        self.assertIn("juniper", str(m))
