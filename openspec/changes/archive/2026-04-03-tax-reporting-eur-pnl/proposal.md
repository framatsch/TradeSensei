## Why

Deutsche Trader müssen für die **Anlage KAP** alle realisierten Gewinne und Verluste in Euro ausweisen. Da Trades bei US-Brokern (IBKR, Schwab) in USD abgewickelt werden, fehlt bisher jede EUR-Denominierung im System — weder auf Trade-Ebene noch in den Metriken. IBKR liefert zwar einen Wechselkurs im CSV-Export mit, dieser wird aber verworfen; Schwab liefert gar keinen. Ohne EUR-Umrechnung ist das Journal für die deutsche Steuererklärung unbrauchbar.

## What Changes

- **Trade-Datenmodell** bekommt zwei neue Felder: `currency` (ISO-4217, z.B. `"USD"`) und `pnl_eur` (realisierter Gewinn/Verlust in Euro zum Kurs zum Abschlusszeitpunkt).
- **IBKR-Parser** liest den bereits vorhandenen Wechselkurs (`FX Rate to Base`) aus dem CSV und befüllt `pnl_eur` direkt.
- **Schwab-Parser** ruft zum Zeitpunkt des Trades (closed_at / opened_at) den EUR/USD-Tages-Wechselkurs von der **Deutschen Bundesbank API** (kostenfrei, kein API-Key) ab und befüllt `pnl_eur`.
- **Wechselkurs-Cache** (DB-Tabelle `fx_rates`) speichert abgerufene Kurse, um API-Calls bei Re-Imports zu vermeiden.
- **Metrics-Service** berechnet `total_pnl_eur` zusätzlich zu `total_pnl`.
- **Neuer Endpunkt `GET /tax/annual-summary`** liefert ein jährliches Steuer-Summary (Gesamtgewinn/-verlust in EUR, aufgeteilt nach Aktien und Derivaten gemäß §20 EStG).
- **Frontend**: Neuer Tab „Steuerbericht" mit Jahresauswahl und Download als CSV für die Anlage KAP.

## Capabilities

### New Capabilities

- `fx-rate-lookup`: Tages-Wechselkurse abrufen und cachen (Bundesbank API + DB-Cache-Tabelle)
- `trade-currency-pnl-eur`: EUR-P&L auf Trade-Ebene speichern und bei Import befüllen
- `tax-annual-summary`: Jahres-Steuer-Endpunkt nach §20 EStG Kategorien (Aktien vs. Derivate)

### Modified Capabilities

- `trade-import`: IBKR liest FX-Rate aus CSV; Schwab ruft Bundesbank-API auf — beide befüllen `pnl_eur`

## Impact

- **DB-Migration**: neue Spalten `currency (VARCHAR 3)`, `pnl_eur (NUMERIC 18,8)` auf `trades`; neue Tabelle `fx_rates`
- **Backend**: neue Datei `utils/fx_rates.py`, angepasste Parser, neuer Router `api/v1/tax.py`, erweiterter Metrics-Service
- **Frontend**: neuer Tab/Page `TaxReport`
- **Dependencies**: kein neues Paket nötig (Bundesbank-API via `httpx` abrufbar, bereits vorhanden)
- **Breaking**: keine — neue Felder sind nullable, bestehende API-Responses bleiben identisch
