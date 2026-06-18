"""Left-sidebar navigation: the "EOL Network" plugin menu."""

from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(
    label="EOL Network",
    icon_class="mdi mdi-calendar-clock",
    groups=(
        (
            "Overview",
            (
                PluginMenuItem(
                    link="plugins:netbox_eol:dashboard",
                    link_text="Dashboard",
                ),
                PluginMenuItem(
                    link="plugins:netbox_eol:settings",
                    link_text="Settings",
                ),
            ),
        ),
        (
            "Lifecycle",
            (
                PluginMenuItem(
                    link="plugins:netbox_eol:lifecycleproduct_list",
                    link_text="Lifecycle Products",
                ),
                PluginMenuItem(
                    link="plugins:netbox_eol:devicetypemapping_list",
                    link_text="Device-Type Mappings",
                ),
                PluginMenuItem(
                    link="plugins:netbox_eol:manufacturervendormap_list",
                    link_text="Manufacturer Map",
                ),
            ),
        ),
    ),
)
