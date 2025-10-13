"""Tests for Home Assistant Metrics Binary Sensor."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.hametrics.const import DOMAIN


async def test_binary_sensor(hass: HomeAssistant, mock_config, mock_opentelemetry):
    """Test the binary sensor state."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state is not None
    assert state.state == "on"


async def test_binary_sensor_failure_after_successful_setup(
    hass: HomeAssistant, mock_config, mocker, mock_opentelemetry
):
    """Test binary sensor state on update failure."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state is not None
    assert state.state == "on"

    mocker.patch(
        "custom_components.hametrics.coordinator.HAMetricsCoordinator._async_update_data",
        side_effect=Exception("Update failed"),
    )

    coordinator = hass.data[DOMAIN]["coordinator"]
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state.state == "off"


async def test_binary_sensor_off_when_last_update_failed_flag(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Binary sensor should be off when last_update_success is False."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    # Initially on
    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state is not None and state.state == "on"

    # Simulate failure without mocking _async_update_data
    coordinator = hass.data[DOMAIN]["coordinator"]
    coordinator.last_update_success = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state.state == "off"


async def test_binary_sensor_off_when_disabled(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Binary sensor should be off when coordinator is disabled."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    # Initially on
    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state is not None and state.state == "on"

    # Disable coordinator
    coordinator = hass.data[DOMAIN]["coordinator"]
    coordinator.enabled = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state.state == "off"


async def test_binary_sensor_recovers_after_failure(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Binary sensor should turn back on after recovering from failure."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN]["coordinator"]

    # Simulate failure
    coordinator.last_update_success = False
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state.state == "off"

    # Recover
    coordinator.last_update_success = True
    coordinator.enabled = True
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.hametrics_connection")
    assert state.state == "on"
