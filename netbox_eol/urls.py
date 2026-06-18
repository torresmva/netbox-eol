"""URL routes for the plugin (mounted under /plugins/eol/)."""

from django.urls import path

from netbox_eol import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("settings/", views.EolSettingsView.as_view(), name="settings"),
    path(
        "lifecycle-products/",
        views.LifecycleProductListView.as_view(),
        name="lifecycleproduct_list",
    ),
    path(
        "device-type-mappings/",
        views.DeviceTypeMappingListView.as_view(),
        name="devicetypemapping_list",
    ),
    path(
        "manufacturer-map/",
        views.ManufacturerVendorMapListView.as_view(),
        name="manufacturervendormap_list",
    ),
]
