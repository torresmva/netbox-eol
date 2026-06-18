"""Plugin views. List views over the cached plugin tables (read-only for now)."""

from netbox.views import generic

from netbox_eol import models, tables


class LifecycleProductListView(generic.ObjectListView):
    queryset = models.LifecycleProduct.objects.all()
    table = tables.LifecycleProductTable


class DeviceTypeMappingListView(generic.ObjectListView):
    queryset = models.DeviceTypeMapping.objects.prefetch_related("device_type", "product")
    table = tables.DeviceTypeMappingTable


class ManufacturerVendorMapListView(generic.ObjectListView):
    queryset = models.ManufacturerVendorMap.objects.prefetch_related("manufacturer")
    table = tables.ManufacturerVendorMapTable
