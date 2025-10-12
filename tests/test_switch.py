"""Tests for Home Assistant Metrics Switch."""

from homeassistant.core import HomeAssistant

from custom_components.hametrics.const import DOMAIN


async def test_switch_initial_state(hass: HomeAssistant, setup_hass):
    """Test the initial state of the switch."""
    state = hass.states.get("switch.hametrics_switch")
    assert state is not None
    assert state.state == "on"


async def test_switch_toggle(hass: HomeAssistant, setup_hass, mock_opentelemetry):
    """Test toggling the switch."""
    coordinator = hass.data[DOMAIN]["coordinator"]

    # Switch ausschalten
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": "switch.hametrics_switch"}
    )
    await hass.async_block_till_done()
    state = hass.states.get("switch.hametrics_switch")
    assert state.state == "off"

    # Coordinator-Update prüfen (keine Metriken gesendet)
    data = await coordinator._async_update_data()
    assert data["enabled"] is False
    assert data["data"] == {}
    mock_opentelemetry.set.assert_not_called()

    # Switch wieder einschalten
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": "switch.hametrics_switch"}
    )
    await hass.async_block_till_done()
    state = hass.states.get("switch.hametrics_switch")
    assert state.state == "on"

    # Coordinator-Update prüfen (Metriken werden gesendet)
    data = await coordinator._async_update_data()
    assert data["enabled"] is True
    assert "ha_temperature_adjusted" in data["data"]
    mock_opentelemetry.set.assert_called()
