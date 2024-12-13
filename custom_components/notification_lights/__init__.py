import asyncio
import logging
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_NAME
import voluptuous as vol

DOMAIN = "notification_lights"
CONF_NOTIFICATION_GROUPS = "notification_groups"
_LOGGER = logging.getLogger(__name__)

CREATE_GROUP_SCHEMA = vol.Schema({
    vol.Required("group_name"): cv.string,
    vol.Required("lights"): vol.All(cv.ensure_list, [cv.entity_id])
})

TRIGGER_SCHEMA = vol.Schema({
    vol.Required("group_name"): cv.string,
    vol.Optional("color"): cv.string,
    vol.Optional("pattern", default={}): dict,
    vol.Optional("duration", default=10): vol.Coerce(float),
    vol.Optional("restore", default=True): bool,
})

async def async_setup(hass: HomeAssistant, config: dict):
    # Initialize data store
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault("groups", {})

    # If you want to define some groups from configuration.yaml, you can still do so:
    domain_config = config.get(DOMAIN, {})
    groups_config = domain_config.get(CONF_NOTIFICATION_GROUPS, [])
    for g in groups_config:
        name = g[CONF_NAME]
        lights = g["lights"]
        hass.data[DOMAIN]["groups"][name] = lights

    async def async_handle_create_group(call: ServiceCall):
        data = call.data
        try:
            validated = CREATE_GROUP_SCHEMA(data)
        except vol.Invalid as err:
            _LOGGER.error("Invalid create_group service call: %s", err)
            return

        group_name = validated["group_name"]
        lights = validated["lights"]

        # Store the group in memory
        hass.data[DOMAIN]["groups"][group_name] = lights
        _LOGGER.info("Created notification group '%s' with lights: %s", group_name, lights)

    async def async_handle_trigger_notification(call: ServiceCall):
        data = call.data
        try:
            validated = TRIGGER_SCHEMA(data)
        except vol.Invalid as err:
            _LOGGER.error("Invalid trigger_notification service call: %s", err)
            return

        group_name = validated["group_name"]
        color = validated.get("color")
        pattern = validated.get("pattern", {})
        duration = validated.get("duration", 10)
        restore = validated.get("restore", True)

        groups = hass.data[DOMAIN]["groups"]

        if group_name not in groups:
            _LOGGER.error("Notification group %s not found", group_name)
            return

        lights = groups[group_name]

        # Save current states
        old_states = {}
        for light in lights:
            old_states[light] = hass.states.get(light)

        # Run the notification pattern
        await run_notification_pattern(hass, lights, color, pattern, duration)

        # Restore states if requested
        if restore:
            await restore_old_states(hass, old_states)

    hass.services.async_register(DOMAIN, "create_group", async_handle_create_group)
    hass.services.async_register(DOMAIN, "trigger_notification", async_handle_trigger_notification)

    return True

async def run_notification_pattern(hass: HomeAssistant, lights: list, color: str, pattern: dict, duration: float):
    if pattern:
        # Extract pattern
        on_time = pattern.get("on", 1.0)
        off_time = pattern.get("off", 1.0)
        repeat = pattern.get("repeat", 3)
        for _ in range(int(repeat)):
            # Turn on
            await turn_on_lights(hass, lights, color)
            await asyncio.sleep(on_time)
            # Turn off
            await turn_off_lights(hass, lights)
            await asyncio.sleep(off_time)
    else:
        # No pattern, just turn on for 'duration'
        await turn_on_lights(hass, lights, color)
        await asyncio.sleep(duration)
        # Restoration will handle turning them off

async def turn_on_lights(hass: HomeAssistant, lights: list, color: str):
    service_data = {}
    if color:
        # Try to parse a hex color
        if color.startswith("#") and len(color) == 7:
            r = int(color[1:3],16)
            g = int(color[3:5],16)
            b = int(color[5:7],16)
            service_data["rgb_color"] = [r, g, b]
        else:
            # If not hex, consider handling named colors or other formats
            pass

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
