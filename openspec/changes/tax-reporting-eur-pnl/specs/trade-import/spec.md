## MODIFIED Requirements

### Requirement: IBKR-Import befüllt EUR-P&L
Der IBKR-Parser SHALL nach dem Parsen der Trades den EUR/USD-Kurs aus der `Forex Balances`-Section des CSV-Exports lesen (Zeile mit `EUR.USD`) und damit `pnl_eur = pnl / rate` für alle geschlossenen Trades befüllen.

#### Scenario: EUR.USD-Kurs in CSV vorhanden
- **WHEN** das IBKR-CSV eine `Forex Balances,Data,...,EUR.USD,...`-Zeile enthält
- **THEN** wird `pnl_eur` für alle Trades mit gesetztem `pnl` berechnet und gesetzt

#### Scenario: EUR.USD-Kurs fehlt im CSV
- **WHEN** kein `EUR.USD`-Eintrag in der `Forex Balances`-Section vorhanden ist
- **THEN** fällt der Parser auf den Bundesbank-API-Lookup für den frühesten Handelstag zurück

#### Scenario: Multi-Tages-Export — Warnung
- **WHEN** das IBKR-CSV Trades über mehrere Kalendertage enthält und nur ein einziger CSV-Kurs verwendet wird
- **THEN** enthält `ImportResult.warnings` eine Warnung über die Ungenauigkeit des einheitlichen Kurses

---

### Requirement: Schwab-Import befüllt EUR-P&L
Der Schwab-Parser SHALL für jedes eindeutige `opened_at.date()` den EUR/USD-Tageskurs via `FxRateService` (Bundesbank API + Cache) abrufen und — sobald `pnl` gesetzt ist — `pnl_eur = pnl / rate` befüllen.

#### Scenario: Kurs für Handelstag verfügbar
- **WHEN** der Bundesbank-Kurs für das `opened_at`-Datum eines Schwab-Trades verfügbar ist
- **THEN** wird `currency = "USD"` und `pnl_eur` korrekt befüllt (sofern `pnl` nicht null)

#### Scenario: Kurs für Handelstag nicht verfügbar
- **WHEN** der Bundesbank-Kurs für das `opened_at`-Datum nicht abrufbar ist
- **THEN** bleibt `pnl_eur = null` und `ImportResult.warnings` enthält einen entsprechenden Hinweis

#### Scenario: Schwab-Trade ist offen (kein pnl)
- **WHEN** ein Schwab-Trade keinen `pnl`-Wert hat (offener Trade)
- **THEN** bleibt `pnl_eur = null` — kein API-Call wird ausgelöst
