"""Config flow for Grafana Cloud Metrics."""

import logging
from typing import Any, Dict, Optional

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_GRAFANA_URL,
    CONF_GRAFANA_USER,
    CONF_GRAFANA_TOKEN,
    CONF_PUSH_INTERVAL,
    CONF_INSTANCE_NAME,
    CONF_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)


class HAMetricsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Cloud Metrics."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate the connection
            try:
                await self._test_connection(
                    user_input[CONF_GRAFANA_URL],
                    user_input[CONF_GRAFANA_USER],
                    user_input[CONF_GRAFANA_TOKEN],
                )

                return self.async_create_entry(title="HA Metrics", data=user_input)

            except Exception as e:
                _LOGGER.error(f"Connection test failed: {e}")
                errors["base"] = "connection_error"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_GRAFANA_URL): str,
                vol.Required(CONF_GRAFANA_USER): str,
                vol.Required(CONF_GRAFANA_TOKEN): str,
                vol.Optional(CONF_INSTANCE_NAME): str,
                vol.Optional(CONF_PUSH_INTERVAL, default=60): int,
                vol.Optional(CONF_ENTITIES, default=[]): cv.ensure_list,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def _test_connection(self, url: str, user: str, token: str):
        """Test the connection to Grafana Cloud."""
        test_url = f"{url}/api/prom/push"

        async with aiohttp.ClientSession() as session:
            auth = aiohttp.BasicAuth(user, token)

            # Send a simple test metric
            test_data = 'test_metric{job="homeassistant"} 1'

            async with session.post(
                test_url,
                data=test_data,
                headers={"Content-Type": "text/plain"},
                auth=auth,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status not in [
                    200,
                    400,
                ]:  # 400 might be expected for malformed data
                    raise Exception(f"HTTP {response.status}")
