import logging
import asyncio
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Notification Lights integration from YAML if present (not used here)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    group_name = entry.data["group_name"]
    lights = entry.data["lights"]

    hass.data[DOMAIN][entry.entry_id] = {
        "group_name": group_name,
        "lights": lights
    }

    # Setup the button platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "button")
    )

    # Register service if not already
    if not hass.services.has_service(DOMAIN, "trigger_notification"):
        async def async_handle_trigger_notification(call):
            entity_id = call.data["entity_id"]
            rgb_color = call.data.get("color")
            pattern_on = call.data.get("pattern_on")
            pattern_off = call.data.get("pattern_off")
            pattern_repeat = call.data.get("pattern_repeat")
            duration = call.data.get("duration", 10)
            restore = call.data.get("restore", True)

            # Build pattern if provided
            pattern = {}
            if pattern_on is not None and pattern_off is not None and pattern_repeat is not None:
                pattern = {
                    "on": pattern_on,
                    "off": pattern_off,
                    "repeat": pattern_repeat
                }

            # Find which entry_id corresponds to this entity_id:
            group_data = await find_group_by_entity_id(hass, entity_id)
            if not group_data:
                _LOGGER.error("Could not find group for entity_id %s", entity_id)
                return

            lights = group_data["lights"]

            old_states = {light: hass.states.get(light) for light in lights}

            await run_notification_pattern(hass, lights, rgb_color, pattern, duration)

            if restore:
                await restore_old_states(hass, old_states)

        hass.services.async_register(DOMAIN, "trigger_notification", async_handle_trigger_notification)

    return True


async def find_group_by_entity_id(hass: HomeAssistant, entity_id: str):
    """Find the group data by searching the entities created."""
    # Since each entry creates one button with a known unique_id, we can look it up:
    # One approach: track entities during setup. Or look up the entity registry.
    # For simplicity, we rely on the entry_id -> group mapping:

    # We know the button entity is associated with a config entry. Let's find the entry:
    registry = await hass.helpers.entity_registry.async_get_registry()
    ent = registry.entities.get(entity_id)
    if ent and ent.config_entry_id in hass.data[DOMAIN]:
        return hass.data[DOMAIN][ent.config_entry_id]
    return None


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    # If you want, you could remove the service if no entries remain:
    # if not hass.data[DOMAIN]:
    #     hass.services.async_remove(DOMAIN, "trigger_notification")
    return True

def _get_all_groups(hass: HomeAssistant):
    """Return a dict of all groups {group_name: [lights]} from all config entries."""
    groups = {}
    for entry_id, data in hass.data[DOMAIN].items():
        groups[data["group_name"]] = data["lights"]
    return groups

async def run_notification_pattern(hass: HomeAssistant, lights: list, rgb_color, pattern: dict, duration: float):
    """Run the notification pattern: if pattern is provided, blink; otherwise just hold for duration."""
    if pattern and "on" in pattern and "off" in pattern and "repeat" in pattern:
        on_time = pattern["on"]
        off_time = pattern["off"]
        repeat = pattern["repeat"]
        for _ in range(int(repeat)):
            await turn_on_lights(hass, lights, rgb_color)
            await asyncio.sleep(on_time)
            await turn_off_lights(hass, lights)
            await asyncio.sleep(off_time)
    else:
        # No pattern, just turn on for duration
        await turn_on_lights(hass, lights, rgb_color)
        await asyncio.sleep(duration)
        # Restoration happens afterwards

async def turn_on_lights(hass: HomeAssistant, lights: list, rgb_color):
    """Turn on the given lights, optionally with a specified RGB color."""
    service_data = {}
    if rgb_color and len(rgb_color) == 3:
        service_data["rgb_color"] = rgb_color

    for light in lights:
        data = {"entity_id": light}
        data.update(service_data)
        await hass.services.async_call("light", "turn_on", data, blocking=True)

async def turn_off_lights(hass: HomeAssistant, lights: list):
    """Turn off the given lights."""
    for light in lights:
        await hass.services.async_call("light", "turn_off", {"entity_id": light}, blocking=True)


async def restore_old_states(hass: HomeAssistant, old_states: dict):
    """Restore the old states of the lights after the notification is done."""
    for entity_id, old_state in old_states.items():
        if old_state is None:
            continue

        attrs = old_state.attributes
        prev_on = (old_state.state == STATE_ON)

        if prev_on:
            data = {"entity_id": entity_id}

            # Restore brightness if present
            if "brightness" in attrs:
                data["brightness"] = attrs["brightness"]

            # Restore color modes:
            # Check hs_color, rgb_color, xy_color, or color_temp - whichever was originally used
            if "hs_color" in attrs:
                data["hs_color"] = attrs["hs_color"]
            elif "rgb_color" in attrs:
                data["rgb_color"] = attrs["rgb_color"]
            elif "xy_color" in attrs:
                data["xy_color"] = attrs["xy_color"]
            elif "color_temp" in attrs:
                data["color_temp"] = attrs["color_temp"]

            await hass.services.async_call("light", "turn_on", data, blocking=True)
        else:
            # Previously off, just turn it off again
            await hass.services.async_call("light", "turn_off", {"entity_id": entity_id}, blocking=True)
