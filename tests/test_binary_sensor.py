"""Tests for Home Assistant Metrics Binary Sensor."""

from homeassistant.core import HomeAssistant

from custom_components.hametrics.const import DOMAIN


async def test_binary_sensor(hass: HomeAssistant, setup_hass):
    """Test the binary sensor state."""
    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state is not None
    assert state.state == "on"


async def test_binary_sensor_failure(hass: HomeAssistant, setup_hass, mocker):
    """Test binary sensor state on update failure."""
    mocker.patch(
        "custom_components.hametrics.coordinator.HAMetricsCoordinator._async_update_data",
        side_effect=Exception("Update failed"),
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    await coordinator.async_request_refresh()
    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state.state == "off"
