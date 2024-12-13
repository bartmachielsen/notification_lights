from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    group_name = entry.data["group_name"]
    lights = entry.data["lights"]

    async_add_entities([NotificationGroupButton(hass, entry.entry_id, group_name, lights)], True)

class NotificationGroupButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, entry_id: str, group_name: str, lights: list):
        self._hass = hass
        self._entry_id = entry_id
        self._group_name = group_name
        self._lights = lights
        self._attr_name = f"{group_name} Notification"
        self._attr_unique_id = f"{entry_id}_notification_button"

    async def async_press(self):
        # No direct action needed here; the service call will handle parameters.
        # But you can call the same code as the service if you'd like a button press to trigger with default settings.
        pass

    @property
    def device_info(self) -> DeviceInfo:
        # Optionally provide device info grouping multiple groups under one device
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=f"Notification Group: {self._group_name}",
            manufacturer="Custom",
        )
