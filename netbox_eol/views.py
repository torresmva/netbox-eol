"""Plugin views: a lifecycle dashboard + read-only list views over the tables."""

from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.views.generic import View

from dcim.models import Device
from netbox.views import generic

from netbox_eol import models, tables


class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        soon = today + timedelta(days=90)
        devices = Device.objects.all()

        def device_count(**flt):
            return devices.filter(**flt).count()

        table = tables.DeviceTypeMappingTable(
            models.DeviceTypeMapping.objects.select_related("device_type", "product")
        )
        table.configure(request)

        context = {
            "total_mapped": models.DeviceTypeMapping.objects.filter(product__isnull=False).count(),
            "needs_review": models.DeviceTypeMapping.objects.filter(product__isnull=True)
            .exclude(match_confidence__in=["", "none"])
            .count(),
            "past_eol_devices": device_count(
                device_type__eol_mapping__product__last_date_of_support__lte=today
            ),
            "eol_soon_devices": device_count(
                device_type__eol_mapping__product__last_date_of_support__gt=today,
                device_type__eol_mapping__product__last_date_of_support__lte=soon,
            ),
            "eos_soon_devices": device_count(
                device_type__eol_mapping__product__end_of_sale_date__gt=today,
                device_type__eol_mapping__product__end_of_sale_date__lte=soon,
            ),
            "kev_devices": device_count(device_type__eol_mapping__product__kev_exposed=True),
            "settings": models.EolSettings.load(),
            "table": table,
        }
        return render(request, "netbox_eol/dashboard.html", context)


class LifecycleProductListView(generic.ObjectListView):
    queryset = models.LifecycleProduct.objects.all()
    table = tables.LifecycleProductTable


class DeviceTypeMappingListView(generic.ObjectListView):
    queryset = models.DeviceTypeMapping.objects.prefetch_related("device_type", "product")
    table = tables.DeviceTypeMappingTable


class ManufacturerVendorMapListView(generic.ObjectListView):
    queryset = models.ManufacturerVendorMap.objects.prefetch_related("manufacturer")
    table = tables.ManufacturerVendorMapTable
