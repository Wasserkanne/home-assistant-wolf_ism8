"""Config flow for Wolf SmartSet Service integration."""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_DEVICES
from homeassistant.const import CONF_HOST
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import NumberSelector
from homeassistant.helpers.selector import NumberSelectorConfig
from homeassistant.helpers.selector import NumberSelectorMode
from wolf_ism8 import Ism8

from .const import CONF_REQUEST_INTERVAL
from .const import CONF_SUPPRESS_UNSUPPORTED
from .const import DEFAULT_HOST
from .const import DEFAULT_PORT
from .const import DEFAULT_REQUEST_INTERVAL
from .const import DOMAIN
from .const import MAX_REQUEST_INTERVAL
from .const import MIN_REQUEST_INTERVAL
from .const import WOLF_DEFAULT_DEVICES

WOLF_HOST_SCHEMA = {
    vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
}

_DEVICE_FIELDS = {}
for _device in Ism8.get_all_devices():
    if _device == "undok_Daten":
        continue
    device_is_default = _device in WOLF_DEFAULT_DEVICES
    _DEVICE_FIELDS[vol.Optional(_device, default=device_is_default)] = cv.boolean

WOLF_DEVICE_SCHEMA = {
    vol.Required("filtering"): section(
        vol.Schema(
            {
                vol.Optional(CONF_SUPPRESS_UNSUPPORTED, default=True): cv.boolean,
            }
        ),
    ),
    vol.Required(CONF_DEVICES): section(
        vol.Schema(_DEVICE_FIELDS),
    ),
}


class WolfConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """wolf config flow"""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow of this entry."""
        return WolfOptionsFlow(config_entry)

    def __init__(self) -> None:
        """Initialize with empty host and port."""
        self.host = None
        self.port = None
        self.devices = None

    async def async_step_user(self, user_input=None):
        """Invoked when a user initiates a flow via the user interface."""
        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            self.host = user_input[CONF_HOST]
            self.port = user_input[CONF_PORT]

            return await self.async_step_device()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(WOLF_HOST_SCHEMA)
        )

    async def async_step_device(self, user_input=None):
        """Invoked when a user initiates a flow via the user interface."""
        if user_input is not None:
            device_selection = user_input.get(CONF_DEVICES) or {}
            self.devices = [
                _device
                for _device in Ism8.get_all_devices()
                if _device != "undok_Daten" and device_selection.get(_device)
            ]

            suppression = (user_input.get("filtering") or {}).get(
                CONF_SUPPRESS_UNSUPPORTED, True
            )

            data = {
                CONF_HOST: self.host,
                CONF_PORT: self.port,
                CONF_DEVICES: self.devices,
                CONF_SUPPRESS_UNSUPPORTED: suppression,
            }

            return self.async_create_entry(title="WOLF ISM8 Adapter", data=data)

        return self.async_show_form(
            step_id="device", data_schema=vol.Schema(WOLF_DEVICE_SCHEMA)
        )

    async def async_step_reconfigure(self, user_input=None):
        """Change the device selection of an entry that is already set up."""
        return await self.async_step_reconfigure_device(user_input)

    async def async_step_reconfigure_device(self, user_input=None):
        """Change the device selection of an entry that is already set up."""
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            device_selection = user_input.get(CONF_DEVICES) or {}
            devices = [
                _device
                for _device in Ism8.get_all_devices()
                if _device != "undok_Daten" and device_selection.get(_device)
            ]

            suppression = (user_input.get("filtering") or {}).get(
                CONF_SUPPRESS_UNSUPPORTED, True
            )

            return self.async_update_reload_and_abort(
                reconfigure_entry,
                data_updates={
                    CONF_HOST: reconfigure_entry.data[CONF_HOST],
                    CONF_PORT: reconfigure_entry.data[CONF_PORT],
                    CONF_DEVICES: devices,
                    CONF_SUPPRESS_UNSUPPORTED: suppression,
                },
            )

        configured = reconfigure_entry.data[CONF_DEVICES]
        return self.async_show_form(
            step_id="reconfigure_device",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(WOLF_DEVICE_SCHEMA),
                {
                    CONF_DEVICES: {
                        _device: _device in configured
                        for _device in Ism8.get_all_devices()
                        if _device != "undok_Daten"
                    },
                    "filtering": {
                        CONF_SUPPRESS_UNSUPPORTED: reconfigure_entry.data.get(
                            CONF_SUPPRESS_UNSUPPORTED, True
                        )
                    },
                },
            ),
        )



class WolfOptionsFlow(config_entries.OptionsFlow):
    """Options: how often all datapoints are requested from the ISM8."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        """Remember the entry to read its current options."""
        self._entry = entry

    async def async_step_init(self, user_input=None):
        """Ask for the request interval."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._entry.options.get(
            CONF_REQUEST_INTERVAL,
            self._entry.data.get(CONF_REQUEST_INTERVAL, DEFAULT_REQUEST_INTERVAL),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_REQUEST_INTERVAL, default=current
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_REQUEST_INTERVAL,
                            max=MAX_REQUEST_INTERVAL,
                            step=1,
                            unit_of_measurement="min",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )
