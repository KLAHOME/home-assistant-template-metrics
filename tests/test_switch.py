"""Tests for Home Assistant Metrics Switch."""

from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.template_metrics.const import COORDINATOR, DOMAIN, GATE


async def test_switch_initial_state(hass: HomeAssistant, mock_config):
    """Test the initial state of the switch."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    state = hass.states.get("switch.template_metrics_switch")
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
        "switch", "turn_off", {"entity_id": "switch.template_metrics_switch"}
    )
    await hass.async_block_till_done()
    state = hass.states.get("switch.template_metrics_switch")
    assert state.state == "off"

    mock_opentelemetry.set.reset_mock()
    data = await coordinator._async_update_data()
    assert data["enabled"] is False
    assert data["data"] == {}
    mock_opentelemetry.set.assert_not_called()

    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.template_metrics_switch"}
    )
    await hass.async_block_till_done()
    state = hass.states.get("switch.template_metrics_switch")
    assert state.state == "on"

    data = await coordinator._async_update_data()
    assert data["enabled"] is True
    assert "ha_temperature_adjusted" in data["data"]
    mock_opentelemetry.set.assert_called()


async def test_switch_restores_off_without_opt_out(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """A saved off state survives a restart and sends no opt-out again."""
    mock_restore_cache(hass, [State("switch.template_metrics_switch", "off")])
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    assert hass.states.get("switch.template_metrics_switch").state == "off"
    coordinator = hass.data[DOMAIN][COORDINATOR]
    assert coordinator.enabled is False
    gate = hass.data[DOMAIN][GATE]
    assert gate.enabled is False
    assert gate._opt_out is False

    mock_opentelemetry.set.reset_mock()
    data = await coordinator._async_update_data()
    assert data["enabled"] is False
    mock_opentelemetry.set.assert_not_called()


async def test_switch_restores_on(hass: HomeAssistant, mock_config, mock_opentelemetry):
    """A saved on state keeps pushing."""
    mock_restore_cache(hass, [State("switch.template_metrics_switch", "on")])
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    assert hass.states.get("switch.template_metrics_switch").state == "on"
    assert hass.data[DOMAIN][GATE].enabled is True


async def test_turn_off_sends_opt_out_once(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Turning off sets opt_in=0 and arms the gate for exactly one export."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    opt_in = mock_opentelemetry.opt_in_gauge
    opt_in.set.assert_called_with(
        1, attributes={"job": "homeassistant", "instance": "test-instance"}
    )
    opt_in.set.reset_mock()
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.template_metrics_switch"}
    )
    await hass.async_block_till_done()

    opt_in.set.assert_called_once_with(
        0, attributes={"job": "homeassistant", "instance": "test-instance"}
    )
    gate = hass.data[DOMAIN][GATE]
    assert gate.enabled is False
    assert gate._opt_out is True

    # A second turn_off while already off does not arm another opt-out
    gate._opt_out = False
    opt_in.set.reset_mock()
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.template_metrics_switch"}
    )
    await hass.async_block_till_done()
    opt_in.set.assert_not_called()
    assert gate._opt_out is False
