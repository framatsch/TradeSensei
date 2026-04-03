## Why

Trades für Aktien, die einen Split oder Reverse Split durchlaufen haben, verbleiben fälschlicherweise als "offen" im Journal, da sich die interne Broker-ID (conid) bei IBKR beim Split ändert und die Kauf- und Verkaufsausführungen nicht mehr korrekt als zusammengehörendes Round-Trip erkannt werden. Ein aktuelles, konkretes Beispiel ist OTLK (1:20 Reverse Split 2024). Da der User seine historischen Daten neu importieren kann, ist jetzt der richtige Zeitpunkt, eine mathematisch korrekte und dauerhaft robuste Lösung zu implementieren.

## What Changes

- **Neue Datenbanktabelle** `corporate_actions` zum Speichern von Split-Events pro User (Symbol, Datum, Ratio, alte/neue Broker-ID).
- **Erweiterung des `Trade` Models** um das Flag `is_manually_edited`, damit manuell korrigierte Trades bei zukünftigen Imports nicht überschrieben werden.
- **Split-aware FIFO Aggregator**: Die Aggregationslogik erkennt Split-Events und rechnet offene Lots (Stückzahl und Einstiegskurs) mathematisch korrekt um, bevor sie gegen schließende Ausführungen gematcht werden. Fractional Shares (Dezimalstückzahlen) werden vollständig unterstützt.
- **Neue REST API** `/api/v1/corporate-actions/` (CRUD) zur Verwaltung von Split-Events.
- **Neue Frontend-Seite "Corporate Actions"** in den Settings, in der der User Splits manuell anlegen, bearbeiten und löschen kann (inkl. Symbol, Datum, Ratio-Eingabe als "Von X zu Y Aktien", alte/neue Broker-ID).
- **Manuelles Trade-Edit**: In der Trade-Detailansicht kann der User Stückzahl und Preis manuell korrigieren, wobei `is_manually_edited` gesetzt wird und zukünftige Imports den Trade nicht mehr anfassen.

## Capabilities

### New Capabilities

- `corporate-action-management`: CRUD-Verwaltung von Corporate Actions (Splits, Reverse Splits) per User. Jede Corporate Action enthält Symbol, Datum, Ratio, optionale alte/neue Broker-ID (conid). Basis für die automatische Korrektur von Trades beim Import.
- `split-aware-aggregation`: Die FIFO-Aggregationslogik für Broker-Importe wird um eine Split-Awareness erweitert. Beim Import werden alle Corporate Actions des Users geladen und bei der Aggregation berücksichtigt: Offene Lots werden zum Zeitpunkt eines Splits automatisch angepasst (Stückzahl * Ratio, Preis / Ratio), sodass die abschließenden Ausführungen korrekt gematcht werden.

### Modified Capabilities

- `trade-import`: Der Importprozess muss Corporate Actions aus der DB laden und an den Aggregator weiterleiten. Das Verhalten bei Imports ändert sich: Trades mit `is_manually_edited = true` werden beim Re-Import nicht überschrieben.

## Impact

- **Backend**: Neues SQLAlchemy Model + Alembic Migration, neues Repository + Service + API Router, Änderung am `aggregate_executions_fifo` in `aggregator.py`, Änderung am `ImportService`.
- **Frontend**: Neuer API-Client (nach openapi-sync), neue Settings-Seite, Anpassung der Trade-Detailansicht.
- **Datenbank**: Schema-Erweiterung (neue Tabelle, neues Feld). Da der User die Daten neu importiert, ist ein Reset der Datenbank akzeptabel.
- **Tests**: Neue Unit-Tests für den Split-aware Aggregator, neue Integration-Tests für die Corporate Actions API.
