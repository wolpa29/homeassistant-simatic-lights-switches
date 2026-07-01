"""Config and subentry flows for the Simatic (S7) integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BIT_OFFSET,
    CONF_DB_NUMBER,
    CONF_LIB,
    CONF_RACK,
    CONF_SENSOR_BIT_OFFSET,
    CONF_SENSOR_DB_NUMBER,
    CONF_SENSOR_START_OFFSET,
    CONF_SLOT,
    CONF_START_OFFSET,
    DOMAIN,
    SUBENTRY_TYPE_LIGHT,
    SUBENTRY_TYPE_SWITCH,
)

CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_RACK, default=0): int,
        vol.Required(CONF_SLOT, default=2): int,
        vol.Optional(CONF_LIB): str,
    }
)

# A light and a switch are configured with the exact same fields: a control
# address (pulsed on turn on/off) and an optional status address.
DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_DB_NUMBER): int,
        vol.Required(CONF_START_OFFSET): int,
        vol.Required(CONF_BIT_OFFSET): int,
        vol.Optional(CONF_SENSOR_DB_NUMBER): int,
        vol.Optional(CONF_SENSOR_START_OFFSET): int,
        vol.Optional(CONF_SENSOR_BIT_OFFSET): int,
    }
)


class SimaticConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the connection to a Simatic PLC."""

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Ask for host, rack and slot."""
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
        return self.async_show_form(step_id="user", data_schema=CONNECTION_SCHEMA)

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry):
        """Lights and switches can both be added under a connection."""
        return {
            SUBENTRY_TYPE_LIGHT: SimaticDeviceSubentryFlow,
            SUBENTRY_TYPE_SWITCH: SimaticDeviceSubentryFlow,
        }


class SimaticDeviceSubentryFlow(ConfigSubentryFlow):
    """Add or edit a single light or switch device."""

    async def async_step_user(self, user_input=None) -> SubentryFlowResult:
        """Add a new device."""
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=DEVICE_SCHEMA)

    async def async_step_reconfigure(self, user_input=None) -> SubentryFlowResult:
        """Edit an existing device."""
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                title=user_input[CONF_NAME],
                data=user_input,
            )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(DEVICE_SCHEMA, subentry.data),
        )
