import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN


# For initial setup, we might not need a lot of input. We can always define an empty initial flow.
# The idea: The user installs the integration, and then via Options Flow, they add groups.
class NotificationLightsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # User confirmed adding the integration.
            return self.async_create_entry(title="Notification Lights", data={"groups": []})

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return NotificationLightsOptionsFlowHandler(config_entry)


class NotificationLightsOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        # Show current groups and allow adding or editing them.
        if user_input is not None:
            # If user selects "add_group", move to another step.
            if user_input.get("action")=="add_group":
                return await self.async_step_add_group()
            elif user_input.get("action")=="edit_groups":
                return await self.async_step_edit_group_select()

        actions = [("add_group", "Add a new group"), ("edit_groups", "Edit or Remove existing groups")]
        data_schema = vol.Schema(
            {
                vol.Required("action", default="add_group"): vol.In({k: v for k, v in actions})
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)

    async def async_step_add_group(self, user_input=None):
        if user_input is not None:
            new_group = {
                "name": user_input["group_name"],
                "lights": [light.strip() for light in user_input["lights"].split(",") if light.strip()]
            }

            groups = self.config_entry.data.get("groups", [])
            # Ensure unique group names
            if any(g["name"]==new_group["name"] for g in groups):
                return self.async_show_form(step_id="add_group", errors={"base": "group_exists"})

            groups.append(new_group)
            new_data = {**self.config_entry.data, "groups": groups}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        data_schema = vol.Schema({
            vol.Required("group_name"): cv.string,
            vol.Required("lights"): cv.string  # comma-separated lights
        })
        return self.async_show_form(step_id="add_group", data_schema=data_schema)

    async def async_step_edit_group_select(self, user_input=None):
        groups = self.config_entry.data.get("groups", [])
        if not groups:
            return self.async_show_form(step_id="edit_group_select", errors={"base": "no_groups"})

        if user_input is not None:
            selected_group = user_input["group"]
            return await self.async_step_edit_group_action(selected_group=selected_group)

        group_names = {g["name"]: g["name"] for g in groups}
        data_schema = vol.Schema({
            vol.Required("group"): vol.In(group_names)
        })
        return self.async_show_form(step_id="edit_group_select", data_schema=data_schema)

    async def async_step_edit_group_action(self, user_input=None, selected_group=None):
        groups = self.config_entry.data.get("groups", [])
        if user_input is not None:
            action = user_input["action"]
            if action=="remove":
                # Remove the group
                updated_groups = [g for g in groups if g["name"]!=selected_group]
                new_data = {**self.config_entry.data, "groups": updated_groups}
                self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
                return self.async_create_entry(title="", data={})
            elif action=="edit":
                # Edit the group
                # Find the group and go to a step to edit lights
                for g in groups:
                    if g["name"]==selected_group:
                        return await self.async_step_edit_group_lights(edit_group=g)

        data_schema = vol.Schema({
            vol.Required("action"): vol.In({"edit": "Edit", "remove": "Remove"})
        })
        return self.async_show_form(step_id="edit_group_action", data_schema=data_schema)

    async def async_step_edit_group_lights(self, user_input=None, edit_group=None):
        groups = self.config_entry.data.get("groups", [])
        if user_input is not None:
            # Update the lights for the group
            new_lights = [light.strip() for light in user_input["lights"].split(",") if light.strip()]
            for g in groups:
                if g["name"]==edit_group["name"]:
                    g["lights"] = new_lights
                    break
            new_data = {**self.config_entry.data, "groups": groups}
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        data_schema = vol.Schema({
            vol.Required("lights", default=",".join(edit_group["lights"])): cv.string
        })
        return self.async_show_form(step_id="edit_group_lights", data_schema=data_schema)
