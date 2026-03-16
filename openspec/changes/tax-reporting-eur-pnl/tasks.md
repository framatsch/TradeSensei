## 1. Datenbank-Migration

- [x] 1.1 Alembic-Migration erstellen: Spalte `currency VARCHAR(3) NULL` auf `trades`
- [x] 1.2 Alembic-Migration erweitern: Spalte `pnl_eur NUMERIC(18,8) NULL` auf `trades`
- [x] 1.3 Alembic-Migration: Neue Tabelle `fx_rates (date DATE, base VARCHAR(3), quote VARCHAR(3), rate NUMERIC(18,8), source VARCHAR(50))` mit Unique-Constraint auf `(date, base, quote)`
- [x] 1.4 Migration reviewen und gegen lokale DB anwenden

## 2. ORM-Modelle und Schemas

- [x] 2.1 `Trade`-ORM-Modell (`backend/app/models/trade.py`) um `currency` und `pnl_eur` erweitern
- [x] 2.2 Neues ORM-Modell `FxRate` in `backend/app/models/fx_rate.py` erstellen
- [x] 2.3 `TradeCreate`-Schema (`backend/app/schemas/trade.py`) um optionale Felder `currency` und `pnl_eur` erweitern
- [x] 2.4 `TradeRead`-Schema um `currency: str | None` und `pnl_eur: Decimal | None` erweitern
- [x] 2.5 Neues Schema `TaxAnnualSummary` in `backend/app/schemas/tax.py` erstellen (inkl. `EquityTaxBlock`, `DerivativesTaxBlock`)

## 3. FX-Rate-Service

- [x] 3.1 Neues Repository `FxRateRepository` in `backend/app/repositories/fx_rate_repository.py` erstellen (get_by_date, upsert)
- [x] 3.2 Neues Utility `backend/app/utils/fx_rates.py` erstellen: `fetch_bundesbank_rate(date)` mit httpx, SDMX-Response parsen, Fallback bis 3 Tage zurück
- [x] 3.3 Neuen Service `FxRateService` in `backend/app/services/fx_rate_service.py` erstellen: Cache-Lookup → API-Fetch → Upsert in DB
- [x] 3.4 Unit-Tests für `fetch_bundesbank_rate`: Mock-Responses für Werktag, Wochenende, Fehlerfall

## 4. IBKR-Parser: EUR-P&L

- [x] 4.1 `IBKRParser` (`backend/app/utils/parsers/ibkr.py`): `Forex Balances`-Section parsen und `EUR.USD`-Rate extrahieren
- [x] 4.2 `IBKRParser._parse_row()`: `currency = "USD"` und `pnl_eur = pnl / rate` befüllen (wenn `pnl IS NOT NULL`)
- [x] 4.3 Fallback: wenn kein CSV-Kurs, `FxRateService` aufrufen für den frühesten Handelstag
- [x] 4.4 Multi-Tages-Warnung: bei `len(unique_trade_dates) > 1` Warnung in `ImportResult.warnings` einfügen
- [x] 4.5 Unit-Tests für IBKR-Parser: EUR.USD vorhanden, EUR.USD fehlend, Multi-Tages-Warnung

## 5. Schwab-Parser: EUR-P&L

- [x] 5.1 `SchwabParser` (`backend/app/utils/parsers/schwab.py`): `FxRateService` als Dependency injizieren (async-fähig machen)
- [x] 5.2 `SchwabParser._parse_row()`: `currency = "USD"` setzen; nach dem Parsen aller Rows für jedes eindeutige Datum den FX-Kurs abrufen und `pnl_eur` befüllen
- [x] 5.3 Warnung bei nicht verfügbarem Kurs in `ImportResult.warnings` einfügen
- [x] 5.4 Unit-Tests für Schwab-Parser: Kurs verfügbar, Kurs nicht verfügbar, offene Trades

## 6. Tax-Endpunkt (Backend)

- [x] 6.1 Neues Repository `TaxRepository` in `backend/app/repositories/tax_repository.py` erstellen: Query für Annual Summary gruppiert nach `asset_class` und `year`
- [x] 6.2 Neuen Service `TaxService` in `backend/app/services/tax_service.py` erstellen: Kategorisierung nach §20 EStG, `total_net_eur` berechnen
- [x] 6.3 Neuen Router `backend/app/api/v1/tax.py` erstellen: `GET /tax/annual-summary?year=YYYY` (JSON)
- [x] 6.4 `GET /tax/annual-summary/csv?year=YYYY` Endpunkt hinzufügen mit `StreamingResponse` und korrekten Headers
- [x] 6.5 Router in `backend/app/api/v1/__init__.py` registrieren
- [x] 6.6 Integrationstests für Tax-Endpunkt: Normaljahr, leeres Jahr, Kategorie-Split, CSV-Download

## 7. Frontend: Steuerbericht-Tab

- [x] 7.1 OpenAPI-Client regenerieren (`openapi-sync`)
- [x] 7.2 Neue Page `frontend/app/(dashboard)/tax/page.tsx` erstellen: Jahres-Auswahl (Dropdown), Summary-Karten (Aktien / Derivate / Gesamt)
- [x] 7.3 Navigation-Eintrag „Steuerbericht" in Sidebar hinzufügen
- [x] 7.4 CSV-Download-Button implementieren (Link auf `GET /tax/annual-summary/csv?year=...`)
- [x] 7.5 Leerzustand-Handling: Info-Box wenn keine EUR-Daten für das gewählte Jahr vorhanden

## 8. Qualitätssicherung

- [x] 8.1 Lint und Typecheck (`lint-check`) auf Backend durchführen und alle Fehler beheben
- [x] 8.2 Alle neuen Tests grün (`unit-test`)
- [x] 8.3 OpenAPI-Docs für neue Endpunkte vervollständigen (`openapi-docs`)
- [x] 8.4 Manuellen End-to-End-Test: IBKR-CSV importieren → `pnl_eur` in DB prüfen → Steuer-Summary aufrufen
