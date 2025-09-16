"""Config flow for Home Assistant Metrics integration."""
import logging
from typing import Any, Dict, Optional
import voluptuous as vol
import requests

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_GRAFANA_URL,
    CONF_GRAFANA_USER,
    CONF_GRAFANA_PASSWORD,
    CONF_HA_INSTANCES,
    CONF_HA_URL,
    CONF_HA_TOKEN,
    CONF_HA_ALIAS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    ERROR_AUTH_FAILED,
    ERROR_CONNECTION_FAILED,
    ERROR_INVALID_URL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GRAFANA_URL): str,
        vol.Required(CONF_GRAFANA_USER): str,
        vol.Required(CONF_GRAFANA_PASSWORD): str,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
    }
)

STEP_HA_INSTANCE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HA_URL): str,
        vol.Required(CONF_HA_TOKEN): str,
        vol.Required(CONF_HA_ALIAS): str,
    }
)


async def validate_grafana_connection(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the Grafana Cloud connection."""
    try:
        # Test Grafana Cloud connection
        auth = (data[CONF_GRAFANA_USER], data[CONF_GRAFANA_PASSWORD])
        test_url = f"{data[CONF_GRAFANA_URL].rstrip('/')}/api/health"
        
        response = await hass.async_add_executor_job(
            requests.get, test_url, {"auth": auth, "timeout": 10}
        )
        
        if response.status_code == 401:
            raise InvalidAuth
        elif response.status_code != 200:
            raise CannotConnect
            
    except requests.exceptions.RequestException:
        raise CannotConnect


async def validate_ha_connection(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the Home Assistant connection."""
    try:
        headers = {
            "Authorization": f"Bearer {data[CONF_HA_TOKEN]}",
            "Content-Type": "application/json",
        }
        test_url = f"{data[CONF_HA_URL].rstrip('/')}/api/"
        
        response = await hass.async_add_executor_job(
            requests.get, test_url, {"headers": headers, "timeout": 10}
        )
        
        if response.status_code == 401:
            raise InvalidAuth
        elif response.status_code != 200:
            raise CannotConnect
            
    except requests.exceptions.RequestException:
        raise CannotConnect


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Assistant Metrics."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}
        self.ha_instances = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_grafana_connection(self.hass, user_input)
                self.data.update(user_input)
                return await self.async_step_ha_instance()
                
            except CannotConnect:
                errors["base"] = ERROR_CONNECTION_FAILED
            except InvalidAuth:
                errors["base"] = ERROR_AUTH_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_ha_instance(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a Home Assistant instance."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_ha_connection(self.hass, user_input)
                self.ha_instances.append(user_input)
                
                # Ask if user wants to add another instance
                return await self.async_step_add_another()
                
            except CannotConnect:
                errors["base"] = ERROR_CONNECTION_FAILED
            except InvalidAuth:
                errors["base"] = ERROR_AUTH_FAILED
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="ha_instance", 
            data_schema=STEP_HA_INSTANCE_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={"instance_count": str(len(self.ha_instances))}
        )

    async def async_step_add_another(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask if user wants to add another Home Assistant instance."""
        if user_input is not None:
            if user_input.get("add_another", False):
                return await self.async_step_ha_instance()
            else:
                # Finalize configuration
                self.data[CONF_HA_INSTANCES] = self.ha_instances
                return self.async_create_entry(
                    title="Home Assistant Metrics", data=self.data
                )

        return self.async_show_form(
            step_id="add_another",
            data_schema=vol.Schema({
                vol.Required("add_another", default=False): bool,
            }),
            description_placeholders={"instance_count": str(len(self.ha_instances))}
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Home Assistant Metrics."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL,
                            self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                        ),
                    ): int,
                }
            ),
        )