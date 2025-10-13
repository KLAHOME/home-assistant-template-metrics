"""Tests for Grafana Metrics Sender setup."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.hametrics.const import DOMAIN


async def test_async_setup(hass: HomeAssistant, mock_config):
    """Test the async setup of the integration."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    assert DOMAIN in hass.data
    assert "coordinator" in hass.data[DOMAIN]
    assert "meter" in hass.data[DOMAIN]
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.last_update_success is True


async def test_async_invalid_config(hass: HomeAssistant, mock_config, mocker):
    """Test setup failure due to invalid config."""
    mock_config[DOMAIN]["instance_id"] = ""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert not await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()
