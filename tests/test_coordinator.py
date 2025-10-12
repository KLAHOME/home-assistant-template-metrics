"""Tests for Home Assistant Metrics Coordinator."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hametrics.coordinator import HAMetricsCoordinator
from custom_components.hametrics.const import DOMAIN


async def test_coordinator_update(
    hass: HomeAssistant, mock_config, setup_hass, mock_opentelemetry
):
    """Test successful coordinator update."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    data = await coordinator._async_update_data()

    assert data["success"] is True
    assert data["enabled"] is True
    assert "data" in data
    assert "ha_temperature_adjusted" in data["data"]
    assert data["data"]["ha_temperature_adjusted"] == pytest.approx(
        24.0
    )  # 20.0 * 1.1 + 2
    assert "ha_uptime_hours" in data["data"]
    mock_opentelemetry.set.assert_called()


async def test_coordinator_disabled(
    hass: HomeAssistant, mock_config, setup_hass, mock_opentelemetry
):
    """Test coordinator when push is disabled."""
    hass.states.async_set("switch.hametrics_push", "off")
    coordinator = hass.data[DOMAIN]["coordinator"]
    coordinator.set_telemetry_enabled(False)
    data = await coordinator._async_update_data()

    assert data["success"] is True
    assert data["enabled"] is False
    assert data["data"] == {}
    mock_opentelemetry.set.assert_not_called()


async def test_coordinator_invalid_template(
    hass: HomeAssistant, mock_config, setup_hass, mock_opentelemetry, caplog
):
    """Test handling of invalid template."""
    mock_config[DOMAIN]["metrics"].append(
        {"name": "invalid_metric", "template": "{{ invalid_sensor | float }}"}
    )
    coordinator = HAMetricsCoordinator(hass, mock_config[DOMAIN])
    data = await coordinator._async_update_data()

    assert "Invalid numeric value" in caplog.text
    assert "invalid_metric" not in data["data"]


async def test_coordinator_update_failure(
    hass: HomeAssistant, mock_config, setup_hass, mocker
):
    """Test coordinator update failure."""
    mocker.patch(
        "homeassistant.helpers.template.Template.async_render",
        side_effect=Exception("Template error"),
    )
    coordinator = hass.data[DOMAIN]["coordinator"]
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
