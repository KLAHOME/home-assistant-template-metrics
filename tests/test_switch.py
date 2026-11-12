"""Tests for Home Assistant Metrics Switch."""

from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.template_metrics.const import (
    COORDINATOR,
    DOMAIN,
    GATE,
    OPT_IN_METRIC,
)
from tests.test_gate import _metrics_data, _names


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


async def _setup(hass: HomeAssistant, mock_config) -> None:
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()


async def _switch(hass: HomeAssistant, service: str) -> None:
    await hass.services.async_call(
        "switch", service, {"entity_id": "switch.template_metrics_switch"}
    )
    await hass.async_block_till_done()


def _exported(exporter) -> list[set[str]]:
    """Metric names of every export that reached the remote write exporter."""
    return [_names(call.args[0]) for call in exporter.export.call_args_list]


async def test_switch_restores_off_without_opt_out(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """A saved off state survives a restart and nothing leaves the instance."""
    mock_restore_cache(hass, [State("switch.template_metrics_switch", "off")])
    await _setup(hass, mock_config)

    assert hass.states.get("switch.template_metrics_switch").state == "off"
    coordinator = hass.data[DOMAIN][COORDINATOR]
    assert coordinator.enabled is False
    # Off from the start: the first refresh neither recorded metrics nor opt-in
    mock_opentelemetry.set.assert_not_called()
    mock_opentelemetry.opt_in_gauge.set.assert_not_called()

    gate = hass.data[DOMAIN][GATE]
    gate.export(_metrics_data(1))
    gate.export(_metrics_data(1))
    mock_opentelemetry.exporter.export.assert_not_called()

    data = await coordinator._async_update_data()
    assert data["enabled"] is False
    mock_opentelemetry.set.assert_not_called()


async def test_switch_restores_on(hass: HomeAssistant, mock_config, mock_opentelemetry):
    """A saved on state keeps pushing."""
    mock_restore_cache(hass, [State("switch.template_metrics_switch", "on")])
    await _setup(hass, mock_config)

    assert hass.states.get("switch.template_metrics_switch").state == "on"
    hass.data[DOMAIN][GATE].export(_metrics_data(1))
    assert _exported(mock_opentelemetry.exporter) == [{OPT_IN_METRIC, "ha_temperature"}]


async def test_turn_off_sends_opt_out_once(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Turning off sends opt_in=0 in exactly one export, then nothing."""
    await _setup(hass, mock_config)
    attributes = {"job": "homeassistant", "instance": "test-instance"}

    opt_in = mock_opentelemetry.opt_in_gauge
    opt_in.set.assert_called_with(1, attributes=attributes)
    opt_in.set.reset_mock()
    await _switch(hass, "turn_off")
    opt_in.set.assert_called_once_with(0, attributes=attributes)

    gate = hass.data[DOMAIN][GATE]
    exporter = mock_opentelemetry.exporter
    gate.export(_metrics_data(0))
    gate.export(_metrics_data(0))
    assert _exported(exporter) == [{OPT_IN_METRIC}]

    # A second turn_off while already off sends no further opt-out
    opt_in.set.reset_mock()
    await _switch(hass, "turn_off")
    opt_in.set.assert_not_called()
    gate.export(_metrics_data(0))
    assert _exported(exporter) == [{OPT_IN_METRIC}]


async def test_turn_on_again_sends_opt_in_immediately(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Off -> on records opt_in=1 at once and exports everything again."""
    await _setup(hass, mock_config)
    await _switch(hass, "turn_off")

    opt_in = mock_opentelemetry.opt_in_gauge
    opt_in.set.reset_mock()
    await _switch(hass, "turn_on")
    opt_in.set.assert_called_once_with(
        1, attributes={"job": "homeassistant", "instance": "test-instance"}
    )

    exporter = mock_opentelemetry.exporter
    exporter.export.reset_mock()
    hass.data[DOMAIN][GATE].export(_metrics_data(1))
    assert _exported(exporter) == [{OPT_IN_METRIC, "ha_temperature"}]

    # Turning on while already on does not record opt_in again
    opt_in.set.reset_mock()
    await _switch(hass, "turn_on")
    opt_in.set.assert_not_called()
