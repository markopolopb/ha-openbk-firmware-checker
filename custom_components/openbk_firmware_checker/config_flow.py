"""Config flow for OpenBK Firmware Checker integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_DEVICES,
    CONF_DEVICE_ID,
    CONF_PLATFORM,
    CONF_UPDATE_INTERVAL,
    CONF_SERVER_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORM_FIRMWARE_MAP,
)

_LOGGER = logging.getLogger(__name__)


class OpenBKConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenBK Firmware Checker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Only allow a single instance
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        
        if user_input is not None:
            return self.async_create_entry(
                title="OpenBK Firmware Checker",
                data={},
                options=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): cv.positive_int,
                vol.Optional(CONF_SERVER_URL): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OpenBKOptionsFlowHandler()


class OpenBKOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for OpenBK Firmware Checker."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        
        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): cv.positive_int,
                vol.Optional(
                    CONF_SERVER_URL,
                    default=options.get(CONF_SERVER_URL, ""),
                ): cv.string,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
