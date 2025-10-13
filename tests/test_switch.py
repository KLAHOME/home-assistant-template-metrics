"""Tests for Home Assistant Metrics Switch."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.hametrics.const import DOMAIN


async def test_switch_initial_state(hass: HomeAssistant, mock_config):
    """Test the initial state of the switch."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    state = hass.states.get("switch.hametrics_switch")
    assert state is not None
    assert state.state == "on"


async def test_switch_toggle(hass: HomeAssistant, mock_config, mock_opentelemetry):
    """Test toggling the switch."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN]["coordinator"]

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.hametrics_switch"}
    )
    await hass.async_block_till_done()
    state = hass.states.get("switch.hametrics_switch")
    assert state.state == "off"

    mock_opentelemetry.set.reset_mock()
    data = await coordinator._async_update_data()
    assert data["enabled"] is False
    assert data["data"] == {}
    mock_opentelemetry.set.assert_not_called()

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.hametrics_switch"}
    )
    await hass.async_block_till_done()
    state = hass.states.get("switch.hametrics_switch")
    assert state.state == "on"

    data = await coordinator._async_update_data()
    assert data["enabled"] is True
    assert "ha_temperature_adjusted" in data["data"]
    mock_opentelemetry.set.assert_called()
