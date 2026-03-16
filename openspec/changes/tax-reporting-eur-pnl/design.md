## Context

Das Tradejournal verarbeitet Trades von IBKR und Schwab, die in USD denominiert sind. Das `Trade`-Modell speichert alle Geldbeträge (`pnl`, `entry_price`, `exit_price`, `commission`) als nackte `NUMERIC(18,8)` ohne Währungsangabe — die Währung liegt implizit auf dem übergeordneten `Account`-Objekt (`Account.currency`, Default `"USD"`).

Deutsche Trader benötigen für die **Anlage KAP** den realisierten P&L in Euro, umgerechnet zum amtlichen Wechselkurs des Handelstages. Die **Deutsche Bundesbank** stellt diese Kurse kostenlos und ohne API-Key über eine offizielle REST-API bereit.

Der IBKR-CSV-Export enthält bereits einen Wechselkurs-Header (`EUR.USD` in der `Forex Balances`-Section), wird aber vom Parser verworfen. Schwab-CSVs liefern keinerlei Währungsinformationen.

## Goals / Non-Goals

**Goals:**
- `pnl_eur` und `currency` pro Trade speichern (nullable — rückwärtskompatibel)
- IBKR-Parser: EUR/USD-Kurs aus dem CSV-Export lesen und `pnl_eur` befüllen
- Schwab-Parser: Tages-EUR/USD-Kurs von der Bundesbank-API abrufen und `pnl_eur` befüllen
- Wechselkurs-Cache in einer `fx_rates`-Tabelle, um redundante API-Calls zu vermeiden
- Neuer Endpunkt `GET /tax/annual-summary?year=YYYY` mit EUR-Gesamtzahlen nach §20 EStG-Kategorien
- Frontend-Tab „Steuerbericht" mit Jahresauswahl und CSV-Download

**Non-Goals:**
- Andere Währungspaare als EUR/USD (kein GBP, CHF, etc. in diesem Iteration)
- Echtzeit-Intraday-Kurse (amtlicher Tageskurs der Bundesbank reicht für §20 EStG)
- Automatische Nachberechnung historischer Trades ohne Re-Import
- Berücksichtigung von Verlustverrechnungstöpfen (Freistellungsauftrag, §20 Abs. 6 EStG-Beschränkungen)
- Steuerformular-Befüllung oder PDF-Export

## Decisions

### 1. Bundesbank API als einzige Wechselkursquelle

**Entscheidung**: Die Deutsche Bundesbank Statistical Data Warehouse API (`https://api.bundesbank.de/service/data/EXR/D.USD.EUR.SP00.A`) liefert den offiziellen EUR/USD-Tageskurs (EZB-Referenzkurs, SDMX-Format).

**Alternativen erwogen**:
- *ECB Data Portal API*: Identische Daten, aber Bundesbank hat zuverlässigeres Uptime-SLA für DE-Nutzer
- *Open Exchange Rates / Fixer.io*: Kosten API-Key, nicht amtlich
- *Statische Jahreskurstabellen*: Wartungsaufwand, nicht automatisierbar

**Rationale**: Amtliche Quelle = steuerrechtlich korrekt, kostenlos, kein API-Key, JSON-fähig über SDMX-REST.

### 2. Wechselkurs-Cache als eigene DB-Tabelle `fx_rates`

**Entscheidung**: Tabelle `fx_rates (date DATE, base VARCHAR(3), quote VARCHAR(3), rate NUMERIC(18,8), source VARCHAR(50))` mit Unique-Constraint auf `(date, base, quote)`.

**Alternativen erwogen**:
- *In-Memory-Cache (Redis)*: Overhead, kein Persistenz über Restarts
- *Pro-Trade inline abrufen, kein Cache*: Bei Bulk-Import von 500 Trades werden 500 HTTP-Requests ausgelöst (Rate-Limiting-Risiko, langsam)
- *File-based Cache*: Nicht skalierbar, Docker-unfreundlich

**Rationale**: DB-Cache ist idempotent, transaktionssicher und persistiert über Deployments. Ein Batch-Import lädt pro Kalendertag maximal einen API-Call aus.

### 3. `pnl_eur` auf Trade-Ebene, nicht nur aggregiert

**Entscheidung**: Neues nullable Column `pnl_eur NUMERIC(18,8)` direkt auf `trades`, befüllt beim Import.

**Alternativen erwogen**:
- *Nur im Metrics-Service berechnen*: `pnl_eur = pnl / rate` on-the-fly — kein Storage, aber Rate-Lookup bei jedem Metrics-Call nötig; nicht filtbar/sortierbar per SQL
- *Separate `trade_tax_details`-Tabelle*: Over-engineering für diesen Use-Case

**Rationale**: Direkt auf der Trade-Zeile ist performant für GROUP BY Jahr/Monat-Queries und ermöglicht spätere Filterung im Frontend.

### 4. IBKR: FX-Rate aus `Forex Balances`-Section des CSV

**Entscheidung**: Der IBKR-Export enthält eine `Forex Balances,Data`-Zeile mit `EUR.USD`-Kurs. Dieser wird einmalig pro Datei geparst und auf alle Trades der Datei angewendet (da IBKR-Exporte typischerweise eine Tagesperiode abdecken).

**Risiko**: Wenn ein IBKR-Export mehrere Tage umfasst, gilt nur ein einziger Tageskurs für alle Trades → Ungenauigkeit. Mitigation: Warnung in `ImportResult.warnings` ausgeben, wenn `opened_at`-Daten der Trades mehrere Kalendertage umfassen.

**Fallback**: Wenn kein `EUR.USD`-Kurs im CSV vorhanden, Bundesbank-API-Lookup für den frühesten Handelstag.

### 5. Schwab: Bundesbank-Lookup per `opened_at`-Datum

**Entscheidung**: Da Schwab keine FX-Informationen liefert, wird für jedes eindeutige `opened_at.date()` der Bundesbank-Tageskurs abgerufen (via Cache).

**Rationale**: Schwab-Trades haben keinen `closed_at` (Schwab-Parser setzt ihn nicht), daher ist `opened_at` der beste verfügbare Referenzzeitpunkt.

### 6. Steuer-Endpunkt: Aktien vs. Derivate nach §20 EStG

**Entscheidung**: `GET /tax/annual-summary?year=YYYY` gibt zurück:
```json
{
  "year": 2025,
  "equities": { "gains_eur": 1200.50, "losses_eur": -300.00, "net_eur": 900.50, "trade_count": 45 },
  "derivatives": { "gains_eur": 500.00, "losses_eur": -800.00, "net_eur": -300.00, "trade_count": 12 },
  "total_net_eur": 600.50
}
```
Mapping: `AssetClass.EQUITY` → Aktien (§20 Abs. 2 Nr. 1); alle anderen (`OPTION`, `FUTURE`, `FOREX`, `CRYPTO`) → Derivate (§20 Abs. 2 Nr. 3).

## Risks / Trade-offs

- **Bundesbank-API-Ausfall beim Import** → Mitigation: `httpx`-Timeout von 5 Sekunden; bei Fehler wird `pnl_eur = None` gesetzt und eine Warnung in `ImportResult.warnings` eingetragen. Import schlägt nicht fehl.
- **IBKR Multi-Tages-Export** → Ungenauer Einheitskurs für alle Trades. Mitigation: Warnung wenn `trade_dates > 1`.
- **Rückwärtskompatibilität** → Alle neuen Felder sind nullable. Bestehende API-Clients erhalten `pnl_eur: null` für historische Trades — kein Breaking Change.
- **Schwab ohne `closed_at`** → `pnl_eur` bleibt NULL da `pnl` selbst NULL ist. Konsistent — keine Falschberechnung.
- **Bundesbank liefert keine Kurse an Wochenenden/Feiertagen** → Mitigation: Lookup-Funktion sucht den letzten verfügbaren Kurs (≤ Handelstag, max. 3 Tage zurück).

## Migration Plan

1. Alembic-Migration: `ALTER TABLE trades ADD COLUMN currency VARCHAR(3)`, `ADD COLUMN pnl_eur NUMERIC(18,8)` (beide nullable)
2. Neue Tabelle `fx_rates` erstellen
3. Backend deployen — bestehende Trades haben `currency=NULL, pnl_eur=NULL`
4. Kein Datenmigrations-Backfill für historische Trades (Out of Scope)
5. Rollback: `ALTER TABLE trades DROP COLUMN pnl_eur, DROP COLUMN currency` + `DROP TABLE fx_rates`

## Open Questions

- Soll die Bundesbank-API auch für manuelle Trade-Erstellungen via `POST /trades` aufgerufen werden (wenn `currency='USD'` und `pnl` gesetzt)? → Vorschlag: ja, optional, async im Background-Task.
- Freistellungsauftrag (801€/1602€) soll im Steuer-Summary angezeigt werden? → In diesem Iteration: nein, nur rohe Zahlen.
