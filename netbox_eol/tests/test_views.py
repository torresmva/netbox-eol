"""NetBox framework tests for the plugin list views."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ListViewsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            "tester", "tester@example.test", "password"
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_views_render(self):
        for name in (
            "lifecycleproduct_list",
            "devicetypemapping_list",
            "manufacturervendormap_list",
        ):
            url = reverse(f"plugins:netbox_eol:{name}")
            with self.subTest(view=name):
                self.assertEqual(self.client.get(url).status_code, 200)
