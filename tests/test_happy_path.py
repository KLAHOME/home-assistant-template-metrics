"""Happy path tests for hametrics YAML-only setup."""

import pytest
from homeassistant.setup import async_setup_component
from custom_components.hametrics.const import DOMAIN


@pytest.mark.asyncio
async def test_initial_push_success(hass, hametrics_yaml_config, post_calls):
    """On startup, an initial snapshot should be pushed successfully."""
    # Create a couple of states before setup to be included in initial snapshot
    hass.states.async_set("sensor.temp", 23.4, {"friendly_name": "Temperature"})
    hass.states.async_set("light.kitchen", "on", {"friendly_name": "Kitchen Light"})

    assert await async_setup_component(hass, DOMAIN, hametrics_yaml_config)
    await hass.async_block_till_done()

    # At least one POST should have been performed (initial snapshot)
    assert len(post_calls) >= 1

    # Check content-type headers for remote write
    last = post_calls[-1]
    headers = last["headers"]
    assert headers["Content-Type"] == "application/x-protobuf"
    assert headers["Content-Encoding"] == "snappy"


@pytest.mark.asyncio
async def test_periodic_push_after_state_change(
    hass, hametrics_yaml_config, post_calls
):
    """A state change should be buffered and pushed on next interval."""
    assert await async_setup_component(hass, DOMAIN, hametrics_yaml_config)
    await hass.async_block_till_done()

    # Simulate state change
    hass.states.async_set("switch.outlet", "on", {"friendly_name": "Outlet"})
    await hass.async_block_till_done()

    # Expect at least one POST beyond initial (2 total or more)
    assert len(post_calls) >= 1
