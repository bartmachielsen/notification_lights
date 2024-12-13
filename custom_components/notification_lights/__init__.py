import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    # Not used much here since we rely on config entries
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up from a config entry."""
    hass.data[DOMAIN][entry.entry_id] = {
        "groups": entry.data.get("groups", [])  # or entry.options.get("groups", [])
    }

    # Register services using the groups from the entry
    async def async_handle_trigger_notification(call):
        group_name = call.data.get("group_name")
        color = call.data.get("color")
        pattern = call.data.get("pattern", {})
        duration = call.data.get("duration", 10)
        restore = call.data.get("restore", True)

        groups = hass.data[DOMAIN][entry.entry_id]["groups"]
        group_map = {group["name"]: group["lights"] for group in groups}

        if group_name not in group_map:
            _LOGGER.error("Notification group %s not found", group_name)
            return

        lights = group_map[group_name]

        # Save current states
        old_states = {}
        for light in lights:
            old_states[light] = hass.states.get(light)

        # Run the notification pattern
        await run_notification_pattern(hass, lights, color, pattern, duration)

        # Restore states if requested
        if restore:
            await restore_old_states(hass, old_states)

    # Register the service. If you prefer a domain-based service name, update accordingly.
    hass.services.async_register(DOMAIN, "trigger_notification", async_handle_trigger_notification)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Unregister services related to this entry if needed.
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True

async def run_notification_pattern(hass: HomeAssistant, lights: list, color: str, pattern: dict, duration: float):
    import asyncio
    if pattern:
        on_time = pattern.get("on", 1.0)
        off_time = pattern.get("off", 1.0)
        repeat = pattern.get("repeat", 3)
        for _ in range(int(repeat)):
            await turn_on_lights(hass, lights, color)
            await asyncio.sleep(on_time)
            await turn_off_lights(hass, lights)
            await asyncio.sleep(off_time)
    else:
        await turn_on_lights(hass, lights, color)
        await asyncio.sleep(duration)

async def turn_on_lights(hass: HomeAssistant, lights: list, color: str):
    if color and color.startswith("#") and len(color) == 7:
        r = int(color[1:3],16)
        g = int(color[3:5],16)
        b = int(color[5:7],16)
        service_data = {"rgb_color": [r, g, b]}
    else:
        service_data = {}

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
        prev_on = (old_state.state == "on")

        if prev_on:
            data = {"entity_id": entity_id}
            if "brightness" in attrs:
                data["brightness"] = attrs["brightness"]
            if "hs_color" in attrs:
                data["hs_color"] = attrs["hs_color"]
            elif "rgb_color" in attrs:
                data["rgb_color"] = attrs["rgb_color"]

            await hass.services.async_call("light", "turn_on", data, blocking=True)
        else:
            await hass.services.async_call("light", "turn_off", {"entity_id": entity_id}, blocking=True)
