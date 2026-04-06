# Trade Aggregation & DB Import - Source of Truth

Dieses Dokument definiert die unveränderlichen Regeln (Invariants) und die exakte Logik, wie historische und zukünftige Trades aggregiert, importiert und berechnet werden. Es dient als **Source of Truth** für zukünftige Refactorings. 

**WICHTIG:** *Jede* Änderung an der Import-Pipeline, dem FIFO-Aggregator oder den Trade-Modellen darf diese Regeln unter keinen Umständen verletzen. 

---

## 1. Das Kernproblem: Sequentieller Import vs. Ground Truth

Die Herausforderung besteht darin, dass Broker-Daten (wie Flex Queries von IBKR) meist jahresweise (2023, 2024, 2025, etc.) in das System importiert werden. Trades können jedoch über Jahresgrenzen hinweg geöffnet bleiben.
- Ein Trade, der 2023 geöffnet und 2025 geschlossen wird, existiert in zwei verschiedenen Exportdateien.
- Corporate Actions (z.B. Aktiensplits) können in der Zwischenzeit stattfinden (z.B. 2024).
- Der "In-Memory Ground Truth" Algorithmus liest alle Dateien gleichzeitig ein und berechnet die exakte P&L. Die Datenbank-Pipeline liest jedoch eine Datei nach der anderen und speichert Zwischenstände ab.

**Das Ziel ist: Die sequenzielle Datenbank-Aggregation MUSS exakt auf den Cent dasselbe Net P&L Ergebnis liefern wie die In-Memory All-at-Once Aggregation.**

---

## 2. Unveränderliche Regeln (Invariants) für die Aggregation

### 2.1 Cross-Year Seed Lots (Die "Brücke" zwischen Importen)
Wenn eine neue Datei (z.B. 2024) importiert wird, muss der Aggregator wissen, welche Positionen aus früheren Importen (z.B. 2023) noch offen sind.
- **Regel:** Der Aggregator wird vorab mit `seed_open_lots` (bereits offene Trades aus der DB) und `seed_orphaned_lots` (bereits geschlossene Legs aus der DB, denen ein Opening Leg fehlt) "geimpft".
- **Datenintegrität:** Die Seed Lots MÜSSEN alle rechnungsrelevanten Eigenschaften der originalen DB-Entität 1:1 in das Speicher-Protokoll (`SeedLotLike`) übertragen.
- **Historischer Bug (2025/2026):** Der `multiplier` (z.B. 100 für Optionen) fehlte im `SeedLotLike` Protokoll. Dies führte dazu, dass über Jahresgrenzen offene Lots beim Schließen den Faktor 1 statt 100 verwendeten, was das P&L massiv verfälschte.

### 2.2 Corporate Actions / Aktiensplits (Das OTLK-Problem)
Aktiensplits (Split oder Reverse Split) verändern die Menge (Quantity) und den Einstiegspreis (Entry Price) von allen **zu diesem Zeitpunkt offenen Lots**.
- **Regel:** Splits müssen *streng chronologisch* während des Durchlaufs des FIFO-Algorithmus angewendet werden – nicht vorher und nicht nachher.
- **Sequenzielles Import-Problem:** Wenn ein Lot 2023 geöffnet wird (z.B. 2200 Shares von OTLK) und 2024 ein Reverse Split (1:20 / Ratio 0.05) stattfindet, ist der Split in der 2024er Datei enthalten. Beim Importieren von 2024 wird der Split in die DB geschrieben.
- **Historischer Bug (2023/2024 - OTLK):** Der Split wurde beim 2024-Import in die DB geschrieben, aber dem FIFO-Aggregator wurden nur die *vor dem Import* existierenden Corporate Actions (`ca_for_parser`) übergeben. Der Split fehlte somit im Aggregator-Kontext. Die 2200 Shares von 2023 wurden nicht auf 110 korrigiert. Als 2024 Verkäufe von 400 Shares reinkamen, wurden diese mit falschen (un-gesplitteten) Preisen und falschen Mengen abgeglichen.
- **Lösung / Goldene Regel:** Die Liste der Corporate Actions (`ca_for_parser`) MUSS im `ImportService` immer **nach** dem Einlesen und Speichern neuer Splits aus der aktuellen Datei komplett neu aus der Datenbank geladen werden, **bevor** `aggregate_executions_fifo` aufgerufen wird. 

### 2.3 Orphaned Legs (Verwaiste Schließungen)
Wenn ein User einen Teil seiner Historie importiert (z.B. nur 2024), kann ein Trade geschlossen werden, der 2023 geöffnet wurde (welcher aber nicht importiert wurde).
- **Regel:** Das Closing Leg wird als `orphaned_lot` in die DB geschrieben. Es bekommt als `entry_price` einen Sentinel-Wert (z.B. `0.001`), um es als verwaist zu markieren, aber das Net P&L bleibt `None` / Null, da der echte Einstiegspreis unbekannt ist.
- **Matching:** Wird später das Jahr 2023 importiert, muss das `orphaned_lot` mit dem neu gefundenen Opening Leg verrechnet werden und das P&L nachträglich eintragen. Dies ist ebenfalls in der Aggregator-Logik am Ende der Queue-Verarbeitung zwingend erforderlich.

### 2.4 EUR/USD Währungsumrechnung
Trades und Cash-Transaktionen (Dividenden, Gebühren) werden oft in Fremdwährungen abgewickelt.
- **Regel:** Die Währungsumrechnung in EUR (`pnl_eur`, `net_pnl_eur`) geschieht stets über den EZB-Referenzkurs (Bundesbank API) zum **Schließungszeitpunkt** (Closed_at) des Trades oder der Transaktion.
- **Fallback:** Ist am Stichtag kein Kurs verfügbar (Wochenende, Feiertag), wird der Kurs der letzten 3 vorherigen Tage verwendet.

---

## 3. Wie garantieren wir 10000% Sicherheit für die Zukunft?

Dokumentation ist geduldig, Code ändert sich. Um *mathematische und absolute Sicherheit* zu garantieren, darf man sich bei kritischen Refactorings niemals auf Menschen verlassen. 

**Der 10000% Ansatz: Executable Specifications (Regression Tests)**

Es wurde ein automatisierter End-to-End Regressionstest (`test_pnl_regression.py`) in die CI/CD Pipeline integriert. Dieser Test simuliert genau den Workflow, an dem wir tagelang gearbeitet haben:
1. Er nimmt die XML-Files (2023, 2024, 2025, Q1 2026).
2. Er jagt diese *nacheinander* durch den Datenbank-Import (`ImportService`), exakt wie ein User es im Frontend tun würde.
3. Danach fragt er die berechnete Net P&L aus der Datenbank ab.
4. Er berechnet unabhängig davon die In-Memory Ground Truth (all-at-once).
5. **Er schlägt hart fehl, wenn die Datenbank auch nur um einen Bruchteil eines Cents von der Ground Truth (z.B. -1488.28) abweicht.**
6. Er testet explizit die Problemfälle: OTLK (Cross-Year Split) und VST/Options (Cross-Year Multiplier).

**Wenn zukünftig ein Refactoring (z.B. an der Datenbank, am Parser oder am Aggregator) durchgeführt wird, ist dieser Test der absolute Schiedsrichter. Ist der Test grün, ist das Refactoring sicher. Schlägt er fehl, hat das Refactoring die Logik zerstört.**

---

## 4. Checkliste für zukünftige Entwickler/KI-Agenten

Bevor du Code in `app/utils/parsers/aggregator.py` oder `app/services/import_service.py` änderst:

- [ ] Lese diese Datei vollständig durch.
- [ ] Verstehe, warum Corporate Actions *während* des Durchlaufs ge-reloaded werden müssen.
- [ ] Verstehe, warum `SeedLotLike` alle Attribute (inkl. Multiplier) exakt übertragen muss.
- [ ] Nach deiner Änderung: Führe `uv run pytest tests/integration/test_pnl_regression.py` aus. Wenn er rot ist, hast du einen Bug eingebaut. Punkt.
