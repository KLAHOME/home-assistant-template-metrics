# home-assistant-metrics
Home Assistant-Komponente, die Entitätszustände und Attribute an Grafana Cloud sendet

## Example config in Home Assistant

```yaml
hametrics:
  grafana_url: "https://prometheus-prod-01-eu-west-0.grafana.net"
  grafana_user: "your_grafana_user"
  grafana_token: "your_grafana_api_token"
  instance_name: "homeassistant_main"  # Optional, standard ist der Location Name
  push_interval: 60  # Sekunden zwischen den Push-Vorgängen
  entities:  # Optional, leer = alle Entitäten
    - sensor.temperature
    - light.living_room
    - switch.outlet_1
```
