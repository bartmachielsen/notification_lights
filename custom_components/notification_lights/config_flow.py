import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

class NotificationLightsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Initial step when user adds the integration."""
        if user_input is not None:
            group_name = user_input["group_name"]
            lights = user_input["lights"]

            # Check if this group name already exists in any current entry to avoid duplicates
            for entry in self._async_current_entries():
                if entry.data.get("group_name") == group_name:
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._schema(),
                        errors={"base": "name_exists"}
                    )

            return self.async_create_entry(
                title=group_name,
                data={
                    "group_name": group_name,
                    "lights": lights
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema()
        )

    def _schema(self):
        return vol.Schema({
            vol.Required("group_name"): cv.string,
            vol.Required("lights"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True)
            )
        })

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        # If you want to add an Options flow later, you can implement it.
        # For now, we don't provide options since all configuration is done at creation time.
        return NotificationLightsOptionsFlow(config_entry)


class NotificationLightsOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        # Currently, no additional options flow implemented.
        return self.async_create_entry(title="", data={})
