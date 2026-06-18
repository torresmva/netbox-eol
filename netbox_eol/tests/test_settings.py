"""NetBox framework tests for the settings view + key management."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from netbox_eol.models import EolSettings


class SettingsViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser("t", "t@example.test", "pw")
        cls.url = reverse("plugins:netbox_eol:settings")

    def setUp(self):
        self.client.force_login(self.user)

    def test_settings_page_renders(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_save_encrypts_key_and_updates_settings(self):
        response = self.client.post(
            self.url,
            {
                "save": "1",
                "api_key": "secret-integration-key",
                "base_url": "https://eol.network/api/v1/",
                "sync_interval_hours": "24",
                "sync_targets": "in_use",
                "auto_accept_tiers": ["exact"],
                "review_tiers": ["prefix", "family"],
            },
        )
        self.assertEqual(response.status_code, 302)
        settings = EolSettings.load()
        self.assertEqual(settings.get_api_key(), "secret-integration-key")
        self.assertEqual(settings.api_key_last4, "-key")
        self.assertNotIn("secret", settings.api_key_ciphertext)
        self.assertEqual(settings.auto_accept_tiers, ["exact"])

    def test_clear_key(self):
        settings = EolSettings.load()
        settings.set_api_key("abcd1234")
        settings.save()
        self.client.post(self.url, {"clear_key": "1"})
        settings = EolSettings.load()
        self.assertEqual(settings.api_key_last4, "")
        self.assertEqual(settings.get_api_key(), "")
