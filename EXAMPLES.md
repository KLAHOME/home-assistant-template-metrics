# Home Assistant Metrics - Beispielkonfigurationen

## Beispiel 1: Einzelne lokale Home Assistant Instanz

```yaml
# In der Home Assistant UI konfiguriert:
Grafana Cloud URL: https://mystack.grafana.net
Grafana Benutzername: 12345  # Ihre Benutzer-ID
Grafana Passwort: glsa_xxx   # Ihr Grafana Cloud API Key

Home Assistant URL: http://homeassistant.local:8123
Access Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Instanz Alias: zuhause

Update Intervall: 60 Sekunden
```

## Beispiel 2: Mehrere Home Assistant Instanzen

```yaml
# Erste Instanz (Haupthaus)
Home Assistant URL: http://192.168.1.100:8123
Access Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Instanz Alias: haupthaus

# Zweite Instanz (Ferienhaus)
Home Assistant URL: https://ferienhaus.mydom.de:8123
Access Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Instanz Alias: ferienhaus

# Dritte Instanz (Büro)
Home Assistant URL: http://buero-ha:8123
Access Token: eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Instanz Alias: buero
```

## Grafana Dashboard Beispiele

### Temperatur-Dashboard

```promql
# Alle Temperatursensoren
{__name__=~"home_assistant_.*",domain="sensor",entity_id=~".*temperature.*"}

# Durchschnittstemperatur pro Instanz
avg by (instance) ({__name__=~"home_assistant_.*",domain="sensor",entity_id=~".*temperature.*"})

# Temperaturdifferenz zwischen Instanzen
{__name__=~"home_assistant_.*",domain="sensor",entity_id=~".*temperature.*",instance="haupthaus"} - 
{__name__=~"home_assistant_.*",domain="sensor",entity_id=~".*temperature.*",instance="ferienhaus"}
```

### Energie-Dashboard

```promql
# Stromverbrauch alle Instanzen
{__name__=~"home_assistant_.*",entity_id=~".*power.*"}

# Gesamtverbrauch pro Instanz
sum by (instance) ({__name__=~"home_assistant_.*",entity_id=~".*power.*"})

# Top 5 Verbraucher
topk(5, {__name__=~"home_assistant_.*",entity_id=~".*power.*"})
```

### Status-Dashboard

```promql
# Alle Lichter die an sind
{__name__=~"home_assistant_.*",domain="light"} > 0

# Anzahl eingeschalteter Geräte pro Instanz
count by (instance) ({__name__=~"home_assistant_.*",domain=~"light|switch"} > 0)

# Türen/Fenster Status
{__name__=~"home_assistant_.*",domain=~"binary_sensor",entity_id=~".*door.*|.*window.*"}
```

### Batterie-Dashboard

```promql
# Niedrige Batterien (unter 20%)
{__name__=~"home_assistant_.*",attribute="battery"} < 20

# Batteriestand pro Gerät
{__name__=~"home_assistant_.*",attribute="battery"}

# Durchschnittlicher Batteriestand pro Instanz
avg by (instance) ({__name__=~"home_assistant_.*",attribute="battery"})
```

## Alert-Beispiele

### Kritische Alerts

```yaml
# Niedrige Batterie
- alert: LowBattery
  expr: {__name__=~"home_assistant_.*",attribute="battery"} < 10
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Batterie niedrig: {{ $labels.friendly_name }}"
    description: "Gerät {{ $labels.friendly_name }} in {{ $labels.instance }} hat nur noch {{ $value }}% Batterie"

# Hoher Stromverbrauch
- alert: HighPowerConsumption
  expr: {__name__=~"home_assistant_.*",entity_id=~".*power.*"} > 3000
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Hoher Stromverbrauch: {{ $labels.friendly_name }}"
    description: "{{ $labels.friendly_name }} verbraucht {{ $value }}W"

# Home Assistant nicht erreichbar
- alert: HomeAssistantDown
  expr: up{job="home-assistant-metrics"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Home Assistant Instanz {{ $labels.instance }} nicht erreichbar"
```

## Erweiterte Konfiguration

### Update-Intervall anpassen

```yaml
# Häufigere Updates (alle 30 Sekunden)
Update Intervall: 30

# Weniger häufige Updates (alle 5 Minuten)
Update Intervall: 300
```

### Netzwerk-Timeouts

Die Komponente verwendet Standard-Timeouts:
- Home Assistant API: 30 Sekunden
- Grafana Cloud API: 30 Sekunden
- Verbindungstest: 10 Sekunden

### Fehlerbehebung

1. **Logs überprüfen**:
   - Einstellungen → System → Protokolle
   - Nach "home_assistant_metrics" filtern

2. **Netzwerk testen**:
   ```bash
   # Home Assistant erreichbar?
   curl -H "Authorization: Bearer YOUR_TOKEN" http://your-ha:8123/api/

   # Grafana Cloud erreichbar?
   curl -u "username:password" https://your-stack.grafana.net/api/health
   ```

3. **Metriken in Grafana prüfen**:
   - Grafana → Explore
   - Query: `{__name__=~"home_assistant_.*"}`