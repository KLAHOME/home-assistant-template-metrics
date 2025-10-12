"""Tests for Grafana Metrics Sender setup."""

import pytest
import base64
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.hametrics.const import DOMAIN


async def test_async_setup(hass: HomeAssistant, mock_config, setup_hass):
    """Test the async setup of the integration."""
    assert DOMAIN in hass.data
    assert "coordinator" in hass.data[DOMAIN]
    assert "meter" in hass.data[DOMAIN]
    coordinator = hass.data[DOMAIN]["coordinator"]
    assert coordinator.last_update_success is True
    # Überprüfe, ob der Switch geladen wurde
    state = hass.states.get("switch.hametrics_telemetry")
    assert state is not None
    assert state.state == "on"


async def test_async_setup_auth_headers(hass: HomeAssistant, mock_config, mocker):
    """Test that the OpenTelemetry headers are correctly set."""
    mock_exporter = mocker.patch(
        "opentelemetry.exporter.prometheus_remote_write.PrometheusRemoteWriteExporter"
    )
    await hass.config_entries.async_setup(mock_config[DOMAIN])
    await hass.async_block_till_done()

    # Überprüfe, ob der Exporter mit korrekten Headers initialisiert wurde
    expected_auth = (
        f"Basic {base64.b64encode('test_instance:test_api_key'.encode()).decode()}"
    )
    mock_exporter.assert_called_once()
    call_args = mock_exporter.call_args
    assert call_args[1]["headers"]["Authorization"] == expected_auth
    assert call_args[1]["endpoint"] == mock_config[DOMAIN]["remote_write_url"]


async def test_async_setup_failure(hass: HomeAssistant, mock_config, mocker):
    """Test setup failure due to coordinator error."""
    mocker.patch(
        "custom_components.hametrics.coordinator.HAMetricsCoordinator.async_config_entry_first_refresh",
        side_effect=Exception("Mocked error"),
    )
    with pytest.raises(ConfigEntryNotReady):
        await hass.config_entries.async_setup(mock_config[DOMAIN])
