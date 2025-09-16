# Home Assistant Metrics

Eine benutzerdefinierte Home Assistant-Komponente, die Entitätszustände und Attribute von mehreren Home Assistant-Instanzen überwacht und als Metriken an Grafana Cloud sendet.

## Features

- 📊 Überwachung von Entitätszuständen und Attributen von mehreren Home Assistant-Instanzen
- 🚀 Automatisches Senden von Metriken an Grafana Cloud via Push-API
- ⚙️ Einfache Konfiguration über die Home Assistant UI
- 🔄 Konfigurierbare Update-Intervalle
- 🌍 Unterstützung für mehrere Home Assistant-Instanzen gleichzeitig
- 📈 Prometheus-kompatibles Metrik-Format

## Installation

### HACS (Empfohlen)

1. Öffnen Sie HACS in Ihrer Home Assistant-Installation
2. Gehen Sie zu "Integrations"
3. Klicken Sie auf die drei Punkte oben rechts und wählen Sie "Custom repositories"
4. Fügen Sie `https://github.com/KLAHOME/home-assistant-metrics` als Repository hinzu
5. Kategorie: "Integration"
6. Installieren Sie die Integration
7. Starten Sie Home Assistant neu

### Manuelle Installation

1. Laden Sie die neueste Version von GitHub herunter
2. Kopieren Sie den Ordner `custom_components/home_assistant_metrics` in Ihr Home Assistant `custom_components` Verzeichnis
3. Starten Sie Home Assistant neu

## Konfiguration

### Grafana Cloud Setup

1. Melden Sie sich bei Grafana Cloud an
2. Notieren Sie sich Ihre Grafana Cloud URL (z.B. `https://your-instance.grafana.net`)
3. Erstellen Sie einen API-Key oder verwenden Sie Ihre Anmeldedaten

### Home Assistant Integration Setup

1. Gehen Sie zu "Einstellungen" > "Geräte & Dienste"
2. Klicken Sie auf "Integration hinzufügen"
3. Suchen Sie nach "Home Assistant Metrics"
4. Folgen Sie dem Konfigurationsassistenten:
   - Geben Sie Ihre Grafana Cloud-Anmeldedaten ein
   - Fügen Sie mindestens eine Home Assistant-Instanz hinzu
   - Konfigurieren Sie das Update-Intervall (Standard: 60 Sekunden)

### Konfiguration einer Home Assistant-Instanz

Für jede zu überwachende Home Assistant-Instanz benötigen Sie:

- **Home Assistant URL**: Die vollständige URL Ihrer HA-Instanz (z.B. `http://homeassistant.local:8123`)
- **Access Token**: Ein langlebiger Zugriffstoken aus den HA-Benutzereinstellungen
- **Instanz-Alias**: Ein eindeutiger Name für diese Instanz (wird in den Metriken verwendet)

#### Access Token erstellen

1. Gehen Sie in Home Assistant zu "Profil" (klicken Sie auf Ihren Namen unten links)
2. Scrollen Sie zu "Langlebige Zugriffstoken"
3. Klicken Sie auf "Token erstellen"
4. Geben Sie einen Namen ein (z.B. "Grafana Metrics")
5. Kopieren Sie das generierte Token

## Verwendung

Nach der Konfiguration:

1. Die Integration erstellt einen Sensor namens "Home Assistant Metrics"
2. Dieser Sensor zeigt die Anzahl der überwachten Entitäten an
3. Alle Entitätszustände und numerischen Attribute werden automatisch an Grafana Cloud gesendet
4. Die Metriken enthalten Labels für:
   - `instance`: Der Instanz-Alias
   - `entity_id`: Die vollständige Entity-ID
   - `domain`: Die Domäne der Entität (z.B. sensor, light, switch)
   - `friendly_name`: Der benutzerfreundliche Name der Entität
   - `attribute`: Name des Attributs (nur für Attribut-Metriken)

## Metrik-Format

Die Metriken werden im Prometheus-Format gesendet:

```
# Hauptzustand einer Entität
home_assistant_state{instance="main",entity_id="sensor.temperature",domain="sensor",friendly_name="Temperature"} 23.5

# Attribut einer Entität
home_assistant_attribute{instance="main",entity_id="sensor.temperature",domain="sensor",friendly_name="Temperature",attribute="battery"} 85
```

## Grafana Dashboard

Beispiel-Queries für Grafana:

```promql
# Alle Temperatursensoren
home_assistant_state{domain="sensor",entity_id=~".*temperature.*"}

# Batteriestände
home_assistant_attribute{attribute="battery"}

# Lichter die eingeschaltet sind
home_assistant_state{domain="light"} > 0
```

## Fehlerbehebung

### Verbindungsprobleme

- Überprüfen Sie die URLs und Anmeldedaten
- Stellen Sie sicher, dass die Home Assistant-Instanzen erreichbar sind
- Überprüfen Sie die Logs unter "Einstellungen" > "System" > "Logs"

### Keine Metriken in Grafana

- Überprüfen Sie die Grafana Cloud-Anmeldedaten
- Stellen Sie sicher, dass die Push-API aktiviert ist
- Überprüfen Sie die Logs auf Fehler beim Senden

## Beitragen

Beiträge sind willkommen! Bitte:

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch
3. Committen Sie Ihre Änderungen
4. Erstellen Sie einen Pull Request

## Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei für Details.
