"""Constants for the Home Assistant Metrics integration."""

DOMAIN = "home_assistant_metrics"

# Configuration keys
CONF_GRAFANA_URL = "grafana_url"
CONF_GRAFANA_USER = "grafana_user"
CONF_GRAFANA_PASSWORD = "grafana_password"
CONF_HA_INSTANCES = "ha_instances"
CONF_HA_URL = "ha_url"
CONF_HA_TOKEN = "ha_token"
CONF_HA_ALIAS = "ha_alias"
CONF_ENTITIES = "entities"
CONF_INCLUDE_ATTRIBUTES = "include_attributes"
CONF_UPDATE_INTERVAL = "update_interval"

# Default values
DEFAULT_UPDATE_INTERVAL = 60  # seconds
DEFAULT_INCLUDE_ATTRIBUTES = True

# Grafana Cloud API endpoints
GRAFANA_METRICS_ENDPOINT = "/api/v1/push"

# Error messages
ERROR_AUTH_FAILED = "Authentication failed"
ERROR_CONNECTION_FAILED = "Connection failed"
ERROR_INVALID_URL = "Invalid URL"