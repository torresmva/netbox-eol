"""Detail-page panels: lifecycle/KEV cards on DeviceType and Device pages."""

from netbox.plugins import PluginTemplateExtension

from netbox_eol.models import DeviceTypeMapping


def _mapping_for(device_type):
    if device_type is None:
        return None
    return (
        DeviceTypeMapping.objects.filter(device_type=device_type).select_related("product").first()
    )


class DeviceTypeLifecyclePanel(PluginTemplateExtension):
    models = ["dcim.devicetype"]

    def right_page(self):
        device_type = self.context["object"]
        mapping = _mapping_for(device_type)
        return self.render(
            "netbox_eol/inc/lifecycle_card.html",
            extra_context={
                "mapping": mapping,
                "product": mapping.product if mapping else None,
                "rollup": False,
            },
        )


class DeviceLifecyclePanel(PluginTemplateExtension):
    models = ["dcim.device"]

    def right_page(self):
        device = self.context["object"]
        mapping = _mapping_for(getattr(device, "device_type", None))
        return self.render(
            "netbox_eol/inc/lifecycle_card.html",
            extra_context={
                "mapping": mapping,
                "product": mapping.product if mapping else None,
                "rollup": True,
            },
        )


template_extensions = [DeviceTypeLifecyclePanel, DeviceLifecyclePanel]
