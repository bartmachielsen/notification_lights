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

async def run_notification_pattern(hass: HomeAssistant, lights: list, rgb_color, pattern: dict, duration: float):
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
        await turn_on_lights(hass, lights, rgb_color)
        await asyncio.sleep(duration)

async def turn_on_lights(hass: HomeAssistant, lights: list, rgb_color):
    service_data = {}
    if rgb_color and len(rgb_color) == 3:
        service_data["rgb_color"] = rgb_color

    for light in lights:
        data = {"entity_id": light}
        data.update(service_data)
        await hass.services.async_call("light", "turn_on", data, blocking=True)

async def turn_off_lights(hass: HomeAssistant, lights: list):
    for light in lights:
        await hass.services.async_call("light", "turn_off", {"entity_id": light}, blocking=True)

async def restore_old_states(hass: HomeAssistant, old_states: dict):
    for entity_id, old_state in old_states.items():
        if old_state is None:
            continue
        attrs = old_state.attributes
        prev_on = (old_state.state == STATE_ON)

        if prev_on:
            data = {"entity_id": entity_id}
            if "brightness" in attrs:
                data["brightness"] = attrs["brightness"]
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
            await hass.services.async_call("light", "turn_off", {"entity_id": entity_id}, blocking=True)
