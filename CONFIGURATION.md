# Beispielkonfiguration für Home Assistant Metrics

## Grafana Cloud Setup

### 1. Grafana Cloud URL
Ihre Grafana Cloud URL sollte so aussehen:
```
https://your-stack-name.grafana.net
```

### 2. Anmeldedaten
Sie können entweder:
- **Benutzername/Passwort**: Ihre normalen Grafana Cloud Anmeldedaten
- **API Key**: Erstellen Sie einen API Key in Grafana Cloud unter "API Keys"

### 3. Prometheus Push Gateway
Stellen Sie sicher, dass Prometheus Push in Ihrer Grafana Cloud Instanz aktiviert ist.

## Home Assistant Instanzen

### Beispiel für lokale Instanz:
```yaml
URL: http://homeassistant.local:8123
Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9... (Ihr Access Token)
Alias: haupthaus
```

### Beispiel für externe Instanz:
```yaml
URL: https://my-ha.duckdns.org:8123
Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9... (Ihr Access Token)  
Alias: ferienhaus
```

## Access Token erstellen

1. In Home Assistant: Profil → Langlebige Zugriffstoken
2. "Token erstellen" klicken
3. Name eingeben (z.B. "Grafana Metrics")
4. Token kopieren und sicher aufbewahren

## Empfohlene Einstellungen

- **Update-Intervall**: 60 Sekunden (Standard)
  - Niedrigere Werte für häufigere Updates
  - Höhere Werte für weniger Netzwerkverkehr
  
- **Überwachte Entitäten**: Automatisch alle numerischen Entitäten
  - Sensoren mit numerischen Werten
  - Schalter (on/off als 1/0)
  - Lichter (on/off als 1/0) 
  - Batteriestand-Attribute
  - Temperatur-, Luftfeuchtigkeit-Attribute

## Grafana Queries

### Beispiel-Dashboards

#### Temperaturen
```promql
home_assistant_state{domain="sensor",entity_id=~".*temperature.*"}
```

#### Batteriestand niedrig
```promql
home_assistant_attribute{attribute="battery"} < 20
```

#### Alle Lichter
```promql
home_assistant_state{domain="light"}
```

#### Stromverbrauch
```promql
home_assistant_state{entity_id=~".*power.*"}
```