"""Tests for the integration."""

import os
import sys
import pytest

from homeassistant.const import CONF_PLATFORM, CONF_NAME
from homeassistant.components.notify import DOMAIN as NOTIFY_DOMAIN

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
    enable_custom_integrations: None,
):  # pylint: disable=unused-argument
    """Enable custom integrations."""
    yield


@pytest.fixture
def config():
    """Fixture for a hametrics configuration."""
    return {
        NOTIFY_DOMAIN: [
            {
                CONF_PLATFORM: DOMAIN,
                CONF_NAME: "hametrics",
                CONF_GRAFANA_URL: "https://grafana.local",
                CONF_GRAFANA_USER: "test_user",
                CONF_GRAFANA_TOKEN: "test_token",
                CONF_PUSH_INTERVAL: 60,
                CONF_INSTANCE_NAME: "homeassistant",
                CONF_ENTITIES: [],
            }
        ]
    }


@pytest.fixture
def config_data():
    """Fixture for a hametrics config flow."""
    return {
        CONF_GRAFANA_URL: "https://grafana.local",
        CONF_GRAFANA_USER: "test_user",
        CONF_GRAFANA_TOKEN: "test_token",
        CONF_PUSH_INTERVAL: 60,
        CONF_INSTANCE_NAME: "homeassistant",
        CONF_ENTITIES: [],
    }
