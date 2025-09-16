"""Tests for Grafana Metrics config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from custom_components.hametrics.const import (
    DOMAIN,
    CONF_GRAFANA_URL,
    CONF_GRAFANA_USER,
    CONF_GRAFANA_TOKEN,
    CONF_PUSH_INTERVAL,
    CONF_INSTANCE_NAME,
    CONF_ENTITIES,
)


class TestConfigFlow:
    """Test the config flow."""

    async def test_form(self, hass):
        """Test we get the form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {}

    async def test_form_valid_connection(self, hass):
        """Test valid connection creates entry."""
        with patch(
            "custom_components.hametrics.config_flow.HAMetricsConfigFlow._test_connection",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_GRAFANA_URL: "https://prometheus-test.grafana.net",
                    CONF_GRAFANA_USER: "test_user",
                    CONF_GRAFANA_TOKEN: "test_token",
                    CONF_INSTANCE_NAME: "test_instance",
                    CONF_PUSH_INTERVAL: 60,
                },
            )

            assert result2["type"] == FlowResultType.CREATE_ENTRY
            assert result2["title"] == "HA Metrics"

    async def test_form_connection_error(self, hass):
        """Test connection error shows error."""
        with patch(
            "custom_components.hametrics.config_flow.HAMetricsConfigFlow._test_connection",
            side_effect=Exception("Connection failed"),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result2 = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_GRAFANA_URL: "https://prometheus-test.grafana.net",
                    CONF_GRAFANA_USER: "invalid_user",
                    CONF_GRAFANA_TOKEN: "invalid_token",
                },
            )

            assert result2["type"] == FlowResultType.FORM
            assert result2["errors"]["base"] == "connection_error"
