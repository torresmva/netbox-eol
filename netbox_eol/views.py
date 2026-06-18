"""Plugin views: settings page, lifecycle dashboard, and list views."""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import View

from dcim.models import Device
from netbox.views import generic

from netbox_eol import forms, models, sync, tables
from netbox_eol.client import EolClient
from netbox_eol.client.exceptions import EolApiError, EolAuthError, EolRateLimited
from netbox_eol.jobs import EolSyncJob


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


class EolSettingsView(LoginRequiredMixin, View):
    template_name = "netbox_eol/settings.html"

    def get(self, request):
        settings = models.EolSettings.load()
        return render(
            request,
            self.template_name,
            {"form": forms.EolSettingsForm(instance=settings), "settings": settings},
        )

    def post(self, request):
        settings = models.EolSettings.load()

        if "test" in request.POST:
            return self._test_connection(request, settings)

        if "sync" in request.POST:
            EolSyncJob.enqueue(manual=True, user=request.user)
            messages.success(request, "Sync queued.")
            return redirect("plugins:netbox_eol:settings")

        if "clear_key" in request.POST:
            settings.api_key_ciphertext = ""
            settings.api_key_last4 = ""
            settings.save()
            messages.success(request, "API key cleared.")
            return redirect("plugins:netbox_eol:settings")

        form = forms.EolSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect("plugins:netbox_eol:settings")
        return render(request, self.template_name, {"form": form, "settings": settings})

    def _test_connection(self, request, settings):
        api_key = settings.get_api_key()
        if not api_key:
            messages.error(request, "No API key set.")
            return redirect("plugins:netbox_eol:settings")
        client = EolClient(
            base_url=settings.base_url, api_key=api_key, user_agent=sync.DEFAULT_USER_AGENT
        )
        try:
            client.match([{"ref": "test", "q": "test-connection"}])
            messages.success(request, "Connection OK — integration key accepted.")
        except EolAuthError as exc:
            if exc.code == "integration_key_required":
                messages.error(
                    request,
                    "Key is valid but not an integration key — generate one in the "
                    "eol.network portal.",
                )
            else:
                messages.error(request, f"Authentication failed: {exc.code}")
        except EolRateLimited as exc:
            messages.warning(request, f"Rate limited: {exc.code}")
        except EolApiError as exc:
            messages.error(request, f"API error: {exc}")
        return redirect("plugins:netbox_eol:settings")


class LifecycleProductListView(generic.ObjectListView):
    queryset = models.LifecycleProduct.objects.all()
    table = tables.LifecycleProductTable


class DeviceTypeMappingListView(generic.ObjectListView):
    queryset = models.DeviceTypeMapping.objects.prefetch_related("device_type", "product")
    table = tables.DeviceTypeMappingTable


class ManufacturerVendorMapListView(generic.ObjectListView):
    queryset = models.ManufacturerVendorMap.objects.prefetch_related("manufacturer")
    table = tables.ManufacturerVendorMapTable
