"""Plugin data models.

Three cached/relational tables extend NetBoxModel (change-logging, journaling,
tags, custom fields). EolSettings is a plain singleton holding plugin config and
sync status. Device-level lifecycle status is computed, never stored.
"""

from datetime import date

from django.db import models

from netbox.models import NetBoxModel

# get_absolute_url() is intentionally omitted until the URL/views exist (later
# step); adding it now would reverse() route names that aren't registered yet.

# --- choice sets (plain tuples; NetBox-form integration comes with the UI step) --

LIFECYCLE_STATUS_CHOICES = [
    ("supported", "Supported"),
    ("end_of_sale", "End of sale"),
    ("aging", "Aging"),
    ("approaching_eol", "Approaching EoL"),
    ("end_of_life", "End of life"),
]

MATCH_METHOD_CHOICES = [
    ("auto", "Auto"),
    ("manual", "Manual"),
    ("none", "None"),
]

MATCH_TIER_CHOICES = [
    ("exact", "Exact"),
    ("prefix", "Prefix"),
    ("family", "Family"),
    ("search", "Search"),
    ("none", "None"),
]

SYNC_TARGET_CHOICES = [
    ("in_use", "In-use device types only"),
    ("all", "All device types"),
]

SYNC_STATUS_CHOICES = [
    ("never", "Never run"),
    ("success", "Success"),
    ("partial", "Partial"),
    ("failed", "Failed"),
]

MAP_SOURCE_CHOICES = [
    ("learned", "Learned"),
    ("manual", "Manual"),
]


class EolSettings(models.Model):
    """Singleton: API key (encrypted), sync policy, and last-sync status."""

    api_key_ciphertext = models.TextField(blank=True, default="")
    api_key_last4 = models.CharField(max_length=4, blank=True, default="")
    base_url = models.URLField(default="https://eol.network/api/v1/")
    sync_enabled = models.BooleanField(default=False)
    sync_interval_hours = models.PositiveIntegerField(default=24)
    auto_accept_tiers = models.JSONField(default=list)
    review_tiers = models.JSONField(default=list)
    sync_targets = models.CharField(max_length=20, choices=SYNC_TARGET_CHOICES, default="in_use")
    last_sync_started = models.DateTimeField(null=True, blank=True)
    last_sync_finished = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES, default="never")
    last_sync_message = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "EOL settings"
        verbose_name_plural = "EOL settings"

    def __str__(self):
        return "eol.network settings"

    def save(self, *args, **kwargs):
        # Enforce a single row.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={"auto_accept_tiers": ["exact"], "review_tiers": ["prefix", "family"]},
        )
        return obj

    def set_api_key(self, plaintext):
        from django.conf import settings as django_settings

        from netbox_eol import crypto

        self.api_key_ciphertext = crypto.encrypt(plaintext or "", django_settings.SECRET_KEY)
        self.api_key_last4 = (plaintext or "")[-4:]

    def get_api_key(self):
        from django.conf import settings as django_settings

        from netbox_eol import crypto

        return crypto.decrypt(self.api_key_ciphertext, django_settings.SECRET_KEY)


class LifecycleProduct(NetBoxModel):
    """Cached eol.network product record (the lifecycle + KEV source of truth)."""

    vendor_slug = models.CharField(max_length=100)
    product_id = models.CharField(max_length=200)
    product_name = models.CharField(max_length=200, blank=True, default="")
    product_type = models.CharField(max_length=100, blank=True, default="")
    applicable_series = models.JSONField(default=list, blank=True)
    series_slug = models.CharField(max_length=100, blank=True, default="")
    category = models.CharField(max_length=50, blank=True, default="")
    lifecycle_status = models.CharField(
        max_length=20, choices=LIFECYCLE_STATUS_CHOICES, blank=True, default=""
    )
    announcement_date = models.DateField(null=True, blank=True)
    end_of_sale_date = models.DateField(null=True, blank=True)
    last_date_of_support = models.DateField(null=True, blank=True)
    end_of_sw_maintenance_date = models.DateField(null=True, blank=True)
    end_of_vuln_security_support_date = models.DateField(null=True, blank=True)
    end_of_routine_failure_analysis_date = models.DateField(null=True, blank=True)
    replacement_product = models.CharField(max_length=200, blank=True, default="")
    replacement_product_name = models.CharField(max_length=200, blank=True, default="")
    kev_exposed = models.BooleanField(default=False)
    kev_count = models.PositiveIntegerField(default=0)
    kev_cve_ids = models.JSONField(default=list, blank=True)
    kev_catalog_version = models.CharField(max_length=50, blank=True, default="")
    kev_updated_at = models.DateTimeField(null=True, blank=True)
    url = models.URLField(blank=True, default="")
    raw = models.JSONField(default=dict, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("vendor_slug", "product_id")
        constraints = [
            models.UniqueConstraint(
                fields=("vendor_slug", "product_id"),
                name="netbox_eol_product_unique",
            )
        ]

    def __str__(self):
        return self.product_name or f"{self.vendor_slug}/{self.product_id}"

    # --- computed lifecycle helpers (drive UI/rollup) --------------------

    def is_past_eol(self, on=None):
        on = on or date.today()
        return self.last_date_of_support is not None and self.last_date_of_support <= on

    def eol_within(self, days, on=None):
        on = on or date.today()
        if self.last_date_of_support is None:
            return False
        return 0 <= (self.last_date_of_support - on).days <= days

    def eos_within(self, days, on=None):
        on = on or date.today()
        if self.end_of_sale_date is None:
            return False
        return 0 <= (self.end_of_sale_date - on).days <= days


class DeviceTypeMapping(NetBoxModel):
    """Resolved match between a NetBox DeviceType and a LifecycleProduct."""

    device_type = models.OneToOneField(
        "dcim.DeviceType", on_delete=models.CASCADE, related_name="eol_mapping"
    )
    product = models.ForeignKey(
        LifecycleProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mappings",
    )
    match_method = models.CharField(max_length=10, choices=MATCH_METHOD_CHOICES, default="none")
    match_confidence = models.CharField(
        max_length=10, choices=MATCH_TIER_CHOICES, blank=True, default=""
    )
    match_query = models.CharField(max_length=200, blank=True, default="")
    vendor_resolved = models.CharField(max_length=100, blank=True, default="")
    is_overridden = models.BooleanField(default=False)
    last_matched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("device_type",)

    def __str__(self):
        return f"{self.device_type} → {self.product or 'unmatched'}"


class ManufacturerVendorMap(NetBoxModel):
    """Maps a NetBox Manufacturer to an eol.network vendor slug for match hints.

    NetBox manufacturer slugs frequently differ from eol.network vendor slugs;
    learned rows come from match results, manual rows are admin-set and protected.
    """

    manufacturer = models.OneToOneField(
        "dcim.Manufacturer", on_delete=models.CASCADE, related_name="eol_vendor_map"
    )
    vendor_slug = models.CharField(max_length=100)
    source = models.CharField(max_length=10, choices=MAP_SOURCE_CHOICES, default="learned")

    class Meta:
        ordering = ("manufacturer",)

    def __str__(self):
        return f"{self.manufacturer} → {self.vendor_slug}"
