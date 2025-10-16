# home-assistant-template-metrics

Home Assistant-Komponente, die Templates rendert

## Example config in Home Assistant

```yaml
template_metrics:
  user: 123456
  token: glc_ey
  remote_write_url: https://prometheus-prod-24-prod-eu-west-2.grafana.net/api/prom/push
  update_interval: 60 # Seconds
  metrics:
    - name: battery_notes_low
      template: >-
        {% set entities = integration_entities("battery_notes") | expand
            | selectattr('attributes.device_class', 'defined')
            | selectattr('attributes.device_class', 'eq', 'battery')
            | selectattr('attributes.battery_type', 'defined')
            | selectattr('attributes.battery_quantity', 'defined')
            | selectattr('attributes.battery_low', 'defined')
            | selectattr('attributes.battery_low', 'eq', True)
            | map(attribute='entity_id')
            | select('search', '_plus')
            | reject('is_hidden_entity')
            | list
            | default %}
        {{ entities | count }}
```
