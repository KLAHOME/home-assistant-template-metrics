# Home Assistant Template Metrics

Home Assistant custom component that renders Jinja templates into Prometheus-compatible metrics, including multi-series and labelled outputs for Grafana dashboards via Prometheus remote write.

## Example config in Home Assistant

```yaml
template_metrics:
  instance_label: ha-main
  user: 123456
  token: glc_ey
  remote_write_url: https://prometheus-prod-1-prod-eu-west-2.grafana.net/api/prom/push
  update_interval: 60 # seconds
  metrics: # must be a numeric value
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

You can also add per-metric attributes that render with Jinja templates. Each
attribute value is evaluated in the same context as the metric template and is
exposed to Prometheus as a label. Render the value either as plain text or as
JSON (for lists or dicts).

```yaml
metrics:
  - name: battery_notes_types
    template: "{{ entities | count }}"
    attributes:
      battery_types: >-
        {% set types = integration_entities("battery_notes") | expand
            | selectattr('attributes.battery_type', 'defined')
            | map(attribute='attributes.battery_type')
            | unique
            | list %}
        {{ types | tojson }}
```

To emit several labelled series from a single metric, return a JSON array where
each object includes a numeric `value` and optional `attributes`. The per-entry
attributes are merged with any metric-level attributes before the gauge is
exported.

```yaml
metrics:
  - name: battery_notes_quantity
    template: >-
      {% set batteries = integration_entities("battery_notes") | expand
          | selectattr('attributes.battery_type', 'defined')
          | selectattr('attributes.battery_quantity', 'defined')
          | selectattr('entity_id', 'search', '_battery_type')
          | list %}
      {% set payload = namespace(series=[]) %}
      {% for battery in batteries if not is_hidden_entity(battery.entity_id) %}
        {% set payload.series = payload.series + [{
          'value': battery.attributes.battery_quantity | int(0),
          'attributes': {
            'type': battery.attributes.battery_type,
            'friendly_name': battery.name,
            'entity_id': battery.entity_id,
          },
        }] %}
      {% endfor %}
      {{ payload.series | tojson }}
  - name: battery_notes_active_quantity
    template: >-
      {% set items = integration_entities("battery_notes") | expand
          | selectattr('attributes.battery_type', 'defined')
          | selectattr('attributes.battery_quantity', 'defined')
          | selectattr('attributes.battery_low', 'defined')
          | selectattr('attributes.battery_low', 'eq', True)
          | selectattr('entity_id', 'search', '_battery_type')
          | list %}
      {% set payload = namespace(series=[]) %}
      {% for item in items if not is_hidden_entity(item.entity_id) %}
        {% set payload.series = payload.series + [{
          'value': item.attributes.battery_quantity | int(0),
          'attributes': {
            'type': item.attributes.battery_type,
            'friendly_name': item.name,
            'entity_id': item.entity_id,
            'domain': item.domain,
            'battery_low': true,
            'list_index': loop.index0,
          },
        }] %}
      {% endfor %}
        {{ payload.series | tojson }}
```

### Grafana dashboard

An example dashboard is provided in `examples/battery_monitoring_dashboard.json`.
Import it in Grafana via *Dashboards → New → Import*, supply the JSON file, and
select your Prometheus datasource when prompted.


