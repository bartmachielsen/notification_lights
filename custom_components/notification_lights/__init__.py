from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.helpers import entity_registry as er
from homeassistant.exceptions import HomeAssistantError
import logging
import asyncio

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    group_name = entry.data["group_name"]
    lights = entry.data["lights"]

    # Store group data
    hass.data[DOMAIN][entry.entry_id] = {
        "group_name": group_name,
        "lights": lights
    }

    # Set up button platform that creates a button entity for this group
    await hass.config_entries.async_forward_entry_setup(entry, "button")

    # Register service if not already
    if not hass.services.has_service(DOMAIN, "trigger_notification"):
        async def async_handle_trigger_notification(call):
            entity_id = call.data["entity_id"]
            rgb_color = call.data.get("color")

            group_data = await find_group_by_entity_id(hass, entity_id)
            if not group_data:
                _LOGGER.error("Could not find group for entity_id %s", entity_id)
                return

            lights = group_data["lights"]
            old_states = {light: hass.states.get(light) for light in lights}

            for _ in range(4):
                await hass.services.async_call("light", "turn_on", {"entity_id": lights, "rgb_color": rgb_color, "brightness": 255}, blocking=True)

                await asyncio.sleep(1)

                await hass.services.async_call("light", "turn_off", {"entity_id": lights}, blocking=True)

                await asyncio.sleep(1)

            await restore_old_states(hass, old_states)

        hass.services.async_register(DOMAIN, "trigger_notification", async_handle_trigger_notification)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data[DOMAIN].pop(entry.entry_id, None)
    await hass.config_entries.async_forward_entry_unload(entry, "button")
    # If no entries remain, optionally remove the service
    # if not hass.data[DOMAIN]:
    #     hass.services.async_remove(DOMAIN, "trigger_notification")
    return True


async def find_group_by_entity_id(hass: HomeAssistant, entity_id: str):
    """Find group data by entity_id."""
    registry = er.async_get(hass)
    ent = registry.entities.get(entity_id)
    if not ent:
        _LOGGER.debug("No entity registry entry found for %s", entity_id)
        return None

    entry_id = ent.config_entry_id
    if not entry_id or entry_id not in hass.data[DOMAIN]:
        _LOGGER.debug("No matching config entry found for %s", entity_id)
        return None

    return hass.data[DOMAIN][entry_id]


async def restore_old_states(hass: HomeAssistant, old_states: dict):
    """Restore the original states of the lights."""
    for entity_id, old_state in old_states.items():
        if old_state is None:
            continue

        # Extract attributes from the old state
        attrs = old_state.attributes
        prev_on = (old_state.state==STATE_ON)

        # Prepare data for restoring the light's state
        data = {"entity_id": entity_id}
        if attrs.get("brightness"):
            data["brightness"] = int(attrs["brightness"])

        if attrs.get("hs_color"):
            data["hs_color"] = attrs["hs_color"]
        elif "rgb_color" in attrs:
            data["rgb_color"] = attrs["rgb_color"]
        elif "xy_color" in attrs:
            data["xy_color"] = attrs["xy_color"]
        elif "color_temp" in attrs:
            data["color_temp"] = attrs["color_temp"]

        # Restore light state
        try:
            await hass.services.async_call("light", "turn_on", data, blocking=True)

            if not prev_on:
                await hass.services.async_call("light", "turn_off", {"entity_id": entity_id}, blocking=True)

        except Exception as e:
            _LOGGER.error("Failed to restore state for %s: %s", entity_id, e)
