"""Pytest fixtures for hametrics (YAML-only setup)."""

import os
import sys
import pytest

from custom_components.hametrics.const import (
    DOMAIN,
    CONF_GRAFANA_URL,
    CONF_GRAFANA_USER,
    CONF_GRAFANA_TOKEN,
    CONF_PUSH_INTERVAL,
    CONF_INSTANCE_NAME,
    CONF_ENTITIES,
)


if "HA_CLONE" in os.environ:
    # Rewire the testing package to the cloned test modules
    sys.modules["pytest_homeassistant_custom_component"] = __import__("tests")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,  # provided by pytest-homeassistant-custom-component
):
    """Enable custom integrations for tests."""
    yield


@pytest.fixture
def hametrics_yaml_config():
    """YAML-style configuration for hametrics (no config flow)."""
    return {
        CONF_GRAFANA_URL: "http://grafana.local",
        CONF_GRAFANA_USER: "test_user",
        CONF_GRAFANA_TOKEN: "test_token",
        CONF_PUSH_INTERVAL: 1,  # speed up interval for tests
        CONF_INSTANCE_NAME: "homeassistant",
        # Explicitly configure which entities are exported
        CONF_ENTITIES: [
            "sensor.temp",
            "light.kitchen",
            "switch.outlet",
            "sensor.demo",
        ],
    }


@pytest.fixture
def post_calls():
    """Collect POST calls performed by the fake session."""
    return []


@pytest.fixture(autouse=True)
def mock_network(monkeypatch, post_calls):
    """Mock network calls and snappy compression used by the integration, capturing POSTs."""

    # Avoid requiring native snappy in tests
    monkeypatch.setattr(
        "custom_components.hametrics.snappy.compress", lambda b: b, raising=True
    )

    class _FakeResponse:
        def __init__(self, status: int = 200, text: str = "OK") -> None:
            self.status = status
            self._text = text

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return self._text

    class _FakeSession:
        def post(self, *args, **kwargs):
            url = args[0] if args else kwargs.get("url")
            post_calls.append(
                {
                    "url": url,
                    "headers": kwargs.get("headers") or {},
                    "data": kwargs.get("data"),
                    "auth": kwargs.get("auth"),
                }
            )
            return _FakeResponse()

        async def close(self):
            return None

    # Replace ClientSession with a fake
    monkeypatch.setattr(
        "custom_components.hametrics.aiohttp.ClientSession",
        lambda *a, **k: _FakeSession(),
        raising=True,
    )

    yield


@pytest.fixture(autouse=True)
async def _cleanup_hametrics(hass):
    """Ensure hametrics is unloaded after each test if it was loaded."""
    yield
    try:
        handler = hass.data.get(DOMAIN, {}).get("handler")
        if handler:
            await handler.async_unload()
    except BaseException:
        pass
