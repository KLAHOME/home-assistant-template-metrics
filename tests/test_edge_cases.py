"""Edge case tests for Grafana Metrics component."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import aiohttp

from custom_components.hametrics import HAMetrics


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def config(self):
        return {
            "grafana_url": "https://test.grafana.net",
            "grafana_user": "test",
            "grafana_token": "token",
            "instance_name": "test",
            "entities": [],
            "push_interval": 60,
        }

    @pytest.fixture
    def ha_metrics(self, hass, config):
        return HAMetrics(hass, config)

    def test_create_metric_with_none_state(self, ha_metrics):
        """Test metric creation with None state."""
        metrics = ha_metrics._create_metric("sensor.test", None)
        assert metrics == []

    def test_create_metric_with_invalid_attributes(self, ha_metrics):
        """Test metric creation with complex invalid attributes."""
        state = MagicMock()
        state.state = "25.5"
        state.attributes = {
            "friendly_name": "Test Sensor",
            "nested_object": {"deep_nested": {"value": "should_be_ignored"}},
            "circular_ref": None,  # Simulate circular reference
            "function": lambda x: x,  # Functions should be ignored
            "bytes_data": b"binary_data",  # Binary data should be ignored
        }

        # Add circular reference
        state.attributes["circular_ref"] = state.attributes

        metrics = ha_metrics._create_metric("sensor.test", state)

        # Should still create at least the state metric
        assert len(metrics) >= 1
        state_metric = next(m for m in metrics if "state" in m["name"])
        assert state_metric["value"] == 25.5

    def test_process_list_attribute_with_invalid_items(self, ha_metrics):
        """Test list processing with invalid items."""
        invalid_list = [
            {"type": "AA", "quantity": 5},  # Valid
            {"type": "BB"},  # Missing quantity
            "invalid_string",  # String instead of dict
            None,  # None value
            {"type": "CC", "quantity": "invalid_number"},  # Invalid number
        ]

        base_labels = {"instance": "test", "entity_id": "test"}

        metrics = ha_metrics._process_list_attribute(
            "test.entity", "test_attr", invalid_list, base_labels, 1634567890000
        )

        # Should only process valid items
        assert len(metrics) == 1  # Only the AA battery
        assert metrics[0]["value"] == 5

    def test_clean_key_with_special_characters(self, ha_metrics):
        """Test key cleaning with various special characters."""
        test_cases = [
            ("normal_key", "normal_key"),
            ("Key With Spaces", "key_with_spaces"),
            ("key-with-dashes", "key_with_dashes"),
            ("key.with.dots", "key_with_dots"),
            ("key@with#special$chars%", "key@with#special$chars%"),
            ("UPPERCASE_KEY", "uppercase_key"),
            ("", ""),
            ("   ", "___"),
        ]

        for input_key, expected in test_cases:
            result = ha_metrics._clean_key(input_key)
            assert result == expected

    @pytest.mark.asyncio
    async def test_push_metrics_with_empty_list(self, ha_metrics):
        """Test push metrics with empty list."""
        await ha_metrics._push_metrics([])
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_push_metrics_timeout(self, ha_metrics):
        """Test push metrics with timeout."""
        metrics = [{"name": "test", "value": 1, "timestamp": 123, "labels": {}}]

        mock_response = MagicMock()
        mock_response.__aenter__.side_effect = asyncio.TimeoutError()
        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        ha_metrics.session = mock_session

        with patch("custom_components.hametrics._LOGGER") as mock_logger:
            await ha_metrics._push_metrics(metrics)
            mock_logger.error.assert_called_with(
                "Timeout pushing metrics to Grafana Cloud"
            )

    @pytest.mark.asyncio
    async def test_push_metrics_network_error(self, ha_metrics):
        """Test push metrics with network error."""
        metrics = [{"name": "test", "value": 1, "timestamp": 123, "labels": {}}]

        mock_session = AsyncMock()
        mock_session.post.side_effect = aiohttp.ClientError("Network error")
        ha_metrics.session = mock_session

        with patch("custom_components.hametrics._LOGGER") as mock_logger:
            await ha_metrics._push_metrics(metrics)
            mock_logger.error.assert_called()

    def test_format_prometheus_metrics_empty(self, ha_metrics):
        """Test formatting empty metrics list."""
        result = ha_metrics._format_prometheus_metrics([])
        assert isinstance(result, bytes)
        # Should still create valid protobuf with no time series

    def test_format_prometheus_metrics_with_unicode(self, ha_metrics):
        """Test formatting metrics with unicode characters."""
        metrics = [
            {
                "name": "test_metric",
                "value": 1.0,
                "timestamp": 1634567890000,
                "labels": {
                    "unicode_label": "测试数据",
                    "emoji_label": "🔋",
                    "german_label": "Bärenpark",
                },
            }
        ]

        result = ha_metrics._format_prometheus_metrics(metrics)
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_periodic_push_with_exception(self, ha_metrics):
        """Test periodic push task with exception in push."""
        ha_metrics._metrics_buffer = [{"test": "data"}]

        with patch.object(ha_metrics, "_push_metrics") as mock_push:
            mock_push.side_effect = Exception("Push failed")

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]

                with patch("custom_components.hametrics._LOGGER") as mock_logger:
                    with pytest.raises(asyncio.CancelledError):
                        await ha_metrics._periodic_push()

                    mock_logger.error.assert_called()

    def test_state_change_listener_with_exception(self, ha_metrics):
        """Test state change listener with exception in processing."""
        event = MagicMock()
        event.data = {"entity_id": "sensor.test", "new_state": MagicMock()}

        with patch.object(ha_metrics, "_create_metric") as mock_create:
            mock_create.side_effect = Exception("Processing failed")

            # Should not raise exception
            ha_metrics._state_change_listener(event)

            # Buffer should remain unchanged
            assert len(ha_metrics._metrics_buffer) == 0
