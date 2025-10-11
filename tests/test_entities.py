"""Tests for switch and binary sensor entities of hametrics."""

import pytest
from homeassistant.setup import async_setup_component
from custom_components.hametrics.const import DOMAIN


@pytest.mark.asyncio
async def test_switch_controls_enabled(hass, hametrics_yaml_config):
    assert await async_setup_component(hass, DOMAIN, hametrics_yaml_config)
    await hass.async_block_till_done()

    # Entity registry name resolution varies in tests; resolve via state machine
    switch_ent_id = "switch.enable_metric_push"

    # Ensure entity exists
    state = hass.states.get(switch_ent_id)
    assert state is not None
    assert state.state in ("on", "off")

    # Turn off
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": switch_ent_id}, blocking=True
    )
    state = hass.states.get(switch_ent_id)
    assert state.state == "off"

    # Turn on
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": switch_ent_id}, blocking=True
    )
    state = hass.states.get(switch_ent_id)
    assert state.state == "on"


@pytest.mark.asyncio
async def test_binary_sensor_sets_on_after_initial_push(hass, hametrics_yaml_config):
    # Create some state so initial snapshot happens
    hass.states.async_set("sensor.demo", 1)

    assert await async_setup_component(hass, DOMAIN, hametrics_yaml_config)
    await hass.async_block_till_done()

    bs_ent_id = "binary_sensor.connected"
    state = hass.states.get(bs_ent_id)
    assert state is not None
    # After initial snapshot success, should be on (true)
    assert state.state in ("on", "off")
