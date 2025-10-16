"""Tests for Home Assistant Metrics Coordinator."""

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.setup import async_setup_component

from custom_components.template_metrics.const import DOMAIN


async def test_coordinator_update(hass: HomeAssistant, mock_config, mock_opentelemetry):
    """Test successful coordinator update."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN]["coordinator"]
    data = await coordinator._async_update_data()

    assert data["success"] is True
    assert data["enabled"] is True
    assert "data" in data
    assert "ha_temperature_adjusted" in data["data"]
    assert data["data"]["ha_temperature_adjusted"] == pytest.approx(
        24.0
    )  # (20.0 * 1.1 + 2)
    mock_opentelemetry.set.assert_called()
    _, kwargs = mock_opentelemetry.set.call_args
    assert kwargs.get("attributes") == {"instance": "test-instance"}


async def test_coordinator_metric_attributes(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Ensure metric-specific attributes are rendered and exported."""
    mock_config[DOMAIN]["metrics"][0]["attributes"] = {
        "battery_types": "{{ '[\"AA\",\"AAA\"]' }}",
        "battery_note": "{{ states('sensor.temp') }}",
    }

    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN]["coordinator"]
    data = await coordinator._async_update_data()

    assert data["success"] is True
    assert data["enabled"] is True
    assert data["data"]["ha_temperature_adjusted"] == pytest.approx(24.0)
    mock_opentelemetry.set.assert_called()
    _, kwargs = mock_opentelemetry.set.call_args
    assert kwargs.get("attributes") == {
        "instance": "test-instance",
        "battery_types": ["AA", "AAA"],
        "battery_note": 20.0,
    }


async def test_coordinator_multi_series_metric(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Handle template responses that describe multiple series."""
    mock_config[DOMAIN]["metrics"] = [
        {
            "name": "battery_quantities",
            "template": "{{ [{\"value\": 3, \"attributes\": {\"type\": \"AA\", \"device\": \"remote\"}}, {\"value\": \"5\", \"attributes\": {\"type\": \"AAA\"}}] | tojson }}",
            "attributes": {
                "category": "{{ 'stock' }}",
            },
        }
    ]

    await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN]["coordinator"]
    mock_opentelemetry.set.reset_mock()
    data = await coordinator._async_update_data()

    expected_series = [
        {
            "value": 3.0,
            "attributes": {
                "instance": "test-instance",
                "category": "stock",
                "type": "AA",
                "device": "remote",
            },
        },
        {
            "value": 5.0,
            "attributes": {
                "instance": "test-instance",
                "category": "stock",
                "type": "AAA",
            },
        },
    ]

    assert data["success"] is True
    assert data["enabled"] is True
    assert data["data"]["battery_quantities"] == expected_series
    assert mock_opentelemetry.set.call_count == 2
    assert mock_opentelemetry.set.call_args_list[0][1].get("attributes") == expected_series[0]["attributes"]
    assert mock_opentelemetry.set.call_args_list[1][1].get("attributes") == expected_series[1]["attributes"]


async def test_coordinator_disabled(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Test coordinator when push is disabled."""
    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN]["coordinator"]
    coordinator.set_enabled(False)
    assert coordinator.enabled is False

    mock_opentelemetry.set.reset_mock()
    data = await coordinator._async_update_data()
    assert data["success"] is True
    assert data["enabled"] is False
    assert data["data"] == {}
    mock_opentelemetry.set.assert_not_called()


async def test_coordinator_update_data_none_value(
    hass: HomeAssistant, mock_config, mock_opentelemetry
):
    """Test coordinator update failure."""
    mock_config[DOMAIN]["metrics"].append(
        {
            "name": "ha_uptime_hours",
            "template": "{{ ((as_timestamp(now()) - as_timestamp(states('sensor.start_time'))) / 3600) | round(2) }}",
        }
    )

    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    hass.states.async_set("sensor.start_time", "2025-10-10T00:00:00+00:00")
    assert await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()

    hass.states.async_set("sensor.start_time", "invalid_timestamp")
    coordinator = hass.data[DOMAIN]["coordinator"]
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_missing_metric_name(hass: HomeAssistant, mock_config, mocker):
    """Test setup failure when a metric is missing the required 'name' field."""
    mock_config[DOMAIN]["metrics"].append(
        {"template": "{{ states('sensor.temp') | float }}"}
    )

    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert not await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()


async def test_invalid_metric_template(
    hass: HomeAssistant, mock_config, mock_opentelemetry, caplog
):
    """Test handling of invalid template."""
    mock_config[DOMAIN]["metrics"].append(
        {
            "name": "invalid_metric",
            "template": "{{ states('sensor.invalid_sensor') | float }}",
        }
    )

    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert not await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()


async def test_invalid_jinja_template(
    hass: HomeAssistant, mock_config, mock_opentelemetry, caplog
):
    """Test handling of syntactically invalid Jinja template."""
    mock_config[DOMAIN]["metrics"].append(
        {"name": "invalid_jinja", "template": "{{ invalid_syntax }}}"}
    )

    await async_setup_component(hass, "homeassistant", {})
    hass.states.async_set("sensor.temp", "20.0")
    assert not await async_setup_component(hass, DOMAIN, mock_config)
    await hass.async_block_till_done()
