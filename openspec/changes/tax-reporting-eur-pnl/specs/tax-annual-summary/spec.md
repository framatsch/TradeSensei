## ADDED Requirements

### Requirement: Jahres-Steuer-Summary-Endpunkt
Das System SHALL einen Endpunkt `GET /tax/annual-summary` bereitstellen, der eine jährliche Zusammenfassung der realisierten Gewinne und Verluste in EUR nach §20 EStG-Kategorien zurückgibt.

#### Scenario: Summary für ein vorhandenes Handelsjahr
- **WHEN** `GET /tax/annual-summary?year=2025` aufgerufen wird und Trades mit `pnl_eur IS NOT NULL` für das Jahr 2025 existieren
- **THEN** gibt der Endpunkt HTTP 200 mit `year`, `equities`, `derivatives`, `total_net_eur` zurück

#### Scenario: Kein Handelsjahr vorhanden
- **WHEN** `GET /tax/annual-summary?year=2020` aufgerufen wird und keine Trades mit `pnl_eur IS NOT NULL` für 2020 vorhanden sind
- **THEN** gibt der Endpunkt HTTP 200 mit allen Werten auf `0` zurück (kein 404)

#### Scenario: Authentifizierung erforderlich
- **WHEN** der Endpunkt ohne gültiges JWT aufgerufen wird
- **THEN** gibt der Endpunkt HTTP 401 zurück

---

### Requirement: Kategorie-Zuordnung nach §20 EStG
Das System SHALL `AssetClass.EQUITY`-Trades als Aktiengewinne/verluste (§20 Abs. 2 Nr. 1 EStG) kategorisieren und alle anderen Asset-Klassen (`OPTION`, `FUTURE`, `FOREX`, `CRYPTO`) als Termingeschäfte/Derivate (§20 Abs. 2 Nr. 3 EStG).

#### Scenario: Aktien-Trade wird korrekt kategorisiert
- **WHEN** ein Trade mit `asset_class = "EQUITY"` und `pnl_eur = 500.00` im Jahr 2025 existiert
- **THEN** erscheint dieser Trade im `equities`-Block des Annual Summary für 2025

#### Scenario: Options-Trade wird als Derivat kategorisiert
- **WHEN** ein Trade mit `asset_class = "OPTION"` und `pnl_eur = -200.00` im Jahr 2025 existiert
- **THEN** erscheint dieser Trade im `derivatives`-Block des Annual Summary für 2025

---

### Requirement: CSV-Export für Anlage KAP
Das System SHALL einen Endpunkt `GET /tax/annual-summary/csv` bereitstellen, der die Steuer-Summary als CSV-Datei zum Download anbietet, geeignet für manuelles Übertragen in die Anlage KAP.

#### Scenario: CSV-Download
- **WHEN** `GET /tax/annual-summary/csv?year=2025` aufgerufen wird
- **THEN** antwortet der Server mit `Content-Type: text/csv`, `Content-Disposition: attachment; filename="steuer_2025.csv"` und dem strukturierten CSV-Inhalt

#### Scenario: CSV-Inhalt enthält alle relevanten Felder
- **WHEN** die CSV-Datei generiert wird
- **THEN** enthält sie mindestens: Symbol, Eröffnungsdatum, Schließungsdatum, P&L in USD, EUR/USD-Kurs, P&L in EUR, Kategorie (Aktie/Derivat)
