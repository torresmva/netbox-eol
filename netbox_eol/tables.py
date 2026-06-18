"""Tables for the plugin list views."""

import django_tables2 as tables

from netbox.tables import NetBoxTable, columns

from netbox_eol import models


class LifecycleProductTable(NetBoxTable):
    actions = columns.ActionsColumn(actions=())
    kev_exposed = columns.BooleanColumn(verbose_name="KEV")

    class Meta(NetBoxTable.Meta):
        model = models.LifecycleProduct
        fields = (
            "vendor_slug",
            "product_id",
            "product_name",
            "lifecycle_status",
            "end_of_sale_date",
            "last_date_of_support",
            "replacement_product",
            "kev_exposed",
            "kev_count",
            "fetched_at",
        )
        default_columns = (
            "vendor_slug",
            "product_id",
            "product_name",
            "lifecycle_status",
            "end_of_sale_date",
            "last_date_of_support",
            "kev_exposed",
            "kev_count",
        )


class DeviceTypeMappingTable(NetBoxTable):
    actions = columns.ActionsColumn(actions=())
    device_type = tables.Column(linkify=True)
    is_overridden = columns.BooleanColumn(verbose_name="Override")

    class Meta(NetBoxTable.Meta):
        model = models.DeviceTypeMapping
        fields = (
            "device_type",
            "product",
            "match_method",
            "match_confidence",
            "vendor_resolved",
            "is_overridden",
            "last_matched_at",
        )
        default_columns = (
            "device_type",
            "product",
            "match_method",
            "match_confidence",
            "is_overridden",
        )


class ManufacturerVendorMapTable(NetBoxTable):
    actions = columns.ActionsColumn(actions=())
    manufacturer = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = models.ManufacturerVendorMap
        fields = ("manufacturer", "vendor_slug", "source")
        default_columns = ("manufacturer", "vendor_slug", "source")
