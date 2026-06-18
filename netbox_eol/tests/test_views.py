"""NetBox framework tests for the plugin views + detail-page panels."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from dcim.models import DeviceType, Manufacturer

from netbox_eol.models import DeviceTypeMapping, LifecycleProduct


class ViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            "tester", "tester@example.test", "password"
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_views_render(self):
        for name in (
            "dashboard",
            "lifecycleproduct_list",
            "devicetypemapping_list",
            "manufacturervendormap_list",
        ):
            url = reverse(f"plugins:netbox_eol:{name}")
            with self.subTest(view=name):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_devicetype_page_shows_lifecycle_panel(self):
        mfg = Manufacturer.objects.create(name="Cisco", slug="cisco")
        dt = DeviceType.objects.create(manufacturer=mfg, model="PA-X", slug="pa-x")
        product = LifecycleProduct.objects.create(
            vendor_slug="cisco", product_id="PA-X", lifecycle_status="end_of_sale"
        )
        DeviceTypeMapping.objects.create(
            device_type=dt, product=product, match_method="auto", match_confidence="exact"
        )
        response = self.client.get(reverse("dcim:devicetype", args=[dt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "eol.network Lifecycle")
        self.assertContains(response, "PA-X")
