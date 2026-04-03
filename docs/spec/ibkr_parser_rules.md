# Rulebook: IBKR Flex Query XML Parser

This document describes the detailed business rules by which the IBKR Flex Query XML Parser (`ibkr_xml.py`) processes trades, executions, and cash transactions, and then aggregates them into final trades (`aggregator.py`).

## 1. General Workflow

1. **Reading the XML file:** The parser expects an IBKR Flex Query XML file (Activity Flex Query or Trade Confirmation). It decodes the bytes as UTF-8.
2. **Extraction of data blocks:**
   - `<Trade>` elements (from Activity Flex Queries)
   - `<Execution>` elements (from Trade Confirmation Queries)
   - `<CashTransaction>` elements (dividends, deposits/withdrawals, etc.)
   - `<TransactionTax>` elements (financial transaction taxes)
   - `<OpenPosition>` elements (for validating final open trades)
3. **Creation of intermediate objects (executions):** Each processed element is first converted into a `TradeCreate` (as a representation of an execution) or a `CashTransactionCreateRequest`.
4. **Aggregation (FIFO):** The generated executions are aggregated chronologically according to the FIFO principle (First-In-First-Out) via the function `aggregate_executions_fifo()` into closed "round-trip" trades or open positions.

---

## 2. Processing of XML Elements

### 2.1 `<Trade>` Elements (Activity Flex Query)
These elements represent trading activities already aggregated by the broker (often on a daily or per-trade basis).

- **Identification:** Requires a `symbol` and a `tradeDate`. If these are missing, the element is skipped.
- **Asset Category Mapping:**
  - `STK` -> Equity (stocks)
  - `OPT` -> Option
  - `FUT`, `FOP` -> Future
  - `CASH`, `FXCFD` -> Forex
  - `CRYPTO` -> Crypto
  - *Special rule `CASH`:* Forex conversions (e.g., exchanging EUR to USD) are **not** recorded as trades. They are filtered out. However, if a commission is incurred, it is recorded as a `CashTransaction` of type `FEE` (FX Conversion Commission).
- **Direction & Quantity:**
  - `quantity > 0` -> `LONG`
  - `quantity < 0` -> `SHORT`
  - The quantity stored in the system (`quantity`) is always the absolute (positive) value.
- **Price determination (3-tier fallback):**
  1. `tradePrice` attribute.
  2. If 0: `tradeMoney` / `quantity` / `multiplier` (absolute).
  3. If 0: `cost` / `quantity` / `multiplier` (absolute).
  - If the price is still <= 0, the execution is ignored.
- **Commission determination:**
  - Since IBKR often splits or zeros out fees (e.g., `ibCommission="0"`, but actual third-party costs are in `commission="-1.50"`), the parser takes the maximum of the absolute values of both fields: `max(abs(ibCommission), abs(commission))`. This prevents double-counting and ensures fees are captured.
- **PnL (Profit and Loss) & Closing:**
  - The field `fifoPnlRealized` is evaluated.
  - If the realized PnL is **not equal to 0**, this means that a position was (partially) closed by this line.
  - In this case, the `closed_at` date is set to `opened_at` + 1 second (since IBKR only provides one timestamp per line, but TradeJournal requires start/end date).

### 2.2 `<Execution>` Elements (Trade Confirmation)

These elements represent granular single executions of an order.

- **Processing:** Similar to `<Trade>`, but uses the fields `execDate`, `execTime`, and `price`.
- There is no fallback via `tradeMoney` or PnL evaluation, since single executions are by definition "just" executions. The actual determination of whether a trade is closed happens later in the aggregator.
- **Commission determination:** Identical to the `Trade` logic (`max(abs(...))`).

### 2.3 `<CashTransaction>` and `<TransactionTax>` Elements

- **CashTransactions:** Dividends, interest, broker fees (FEE), deposits (DEPOSIT), and withdrawals (WITHDRAWAL). These are directly mapped to internal categories based on text patterns in the IBKR `type` field.
- **TransactionTax:** Financial transaction taxes (e.g., in France or Italy) are recorded as `CashTransaction` of type `FEE`, so they appear in the cash book and are deducted from overall performance.

---

## 3. FIFO Aggregation & Trade Summary (`aggregator.py`)

After all executions (from both `<Trade>` and `<Execution>`) are available as a list of "partial trades" (executions), buys and sells must be matched.

### 3.1 Queue Principle

The aggregator uses the attribute `broker_conid` (the unique IBKR Contract ID) or, alternatively, `(symbol, asset_class)` as a unique key for a financial instrument.
There are two queues:
- **`open_lots`**: Holds all positions that have been opened but not yet (fully) closed.
- **`orphaned_lots`**: Holds "orphaned" closings. This happens when a sale is imported for which no purchase exists in the system (e.g., because the purchase was in the past and the XML file only covers the current month).

### 3.2 Matching Rules (First-In-First-Out)

Executions are processed chronologically:

1. **Opening:**
   If an execution arrives whose direction (`LONG`/`SHORT`) matches the direction of the queue (or the queue is empty), the execution is appended to the end of the `open_lots` queue.

2. **Closing / Countertrade:**
   If the execution has the *opposite* direction to the queue (e.g., queue holds LONGs, current execution is SHORT), the order is matched against the oldest open positions (lots) in the queue.

   - **Match quantity:** Determine how much of the current execution can be matched against the oldest open lot (`min(open_lot.qty, execution.qty)`).
   - **Split commissions:** The commissions of the opening and closing lots are split proportionally to the matched quantity.
   - **Trade completion:** A finished `TradeCreate` (round-trip trade) is created. This receives as start date (`opened_at`) and entry price (`entry_price`) the values of the open lot, and as end date (`closed_at`) and exit price (`exit_price`) the values of the closing execution.
   - **Remaining quantities:** If the closing execution is larger than the open lot, the open lot is completely closed and removed from the queue, and the remaining quantity of the closing execution is matched against the next open lot.

3. **Orphaned Lots:**
   If a closing execution cannot be fully matched against open lots (because the `open_lots` queue is empty), the remaining part is placed in the `orphaned_lots` queue. These are handled later if matching purchases are imported via cross-imports (historical files).

### 3.3 Corporate Actions (Splits / Reverse-Splits)

Stock splits (corporate actions) are processed chronologically *during* FIFO aggregation.
- If the date of an execution exceeds the date of a recorded split, the entire queue of the affected stock is adjusted.
- **Rule:** `lot.quantity *= ratio` and `lot.entry_price /= ratio`.
- If the split changes the IBKR Contract ID (`old_conid` -> `new_conid`), the queue is internally switched to the new key.

### 3.4 Seed Lots (Database State)

To preserve historical relationships, the aggregator can be pre-filled with `seed_open_lots` (open trades already existing in the DB).
If a seed lot is closed, the aggregator generates an update (via `db_trade_id`) instead of persisting a completely new trade.

### 3.5 Final Validation of Open Positions

At the very end, the parser checks the remaining open trades in the `open_lots` queue against the XML block `<OpenPosition>`.
- **Rule:** If the XML file contains `<OpenPosition>` elements (and thus serves as a complete status report), but the open trade does *not* appear as a contract ID in this list, the system assumes that the position was closed outside a regular trade (e.g., write-off, worthless expiration of options).
- **Action:** The trade is "force-closed". The `closed_at` date is set to `opened_at` + 1s, the exit price equals the entry price (0 PnL, pure fee loss), and a note is added: `[Force-closed: not in IBKR open positions]`.
# Fachliches Regelwerk: IBKR Flex Query XML Parser

Dieses Dokument beschreibt die detaillierten fachlichen Regeln, nach denen der IBKR Flex Query XML Parser (`ibkr_xml.py`) Trades, Executions und Cash-Transaktionen verarbeitet und anschließend zu finalen Trades aggregiert (`aggregator.py`).

## 1. Allgemeiner Ablauf

1. **Einlesen der XML-Datei:** Der Parser erwartet eine IBKR Flex Query XML-Datei (Activity Flex Query oder Trade Confirmation). Er dekodiert die Bytes als UTF-8.
2. **Extraktion von Datenblöcken:**
   - `<Trade>` Elemente (aus Activity Flex Queries)
   - `<Execution>` Elemente (aus Trade Confirmation Queries)
   - `<CashTransaction>` Elemente (Dividenden, Ein-/Auszahlungen etc.)
   - `<TransactionTax>` Elemente (Finanztransaktionssteuern)
   - `<OpenPosition>` Elemente (zur Validierung der finalen offenen Trades)
3. **Erzeugung von Zwischenobjekten (Executions):** Jedes verarbeitete Element wird zunächst in ein `TradeCreate` (als Repräsentation einer Ausführung) oder ein `CashTransactionCreateRequest` umgewandelt.
4. **Aggregation (FIFO):** Die generierten Ausführungen (Executions) werden chronologisch nach dem FIFO-Prinzip (First-In-First-Out) über die Funktion `aggregate_executions_fifo()` zu geschlossenen "Round-Trip" Trades oder offenen Positionen zusammengefasst.

---

## 2. Verarbeitung der XML Elemente

### 2.1 `<Trade>` Elemente (Activity Flex Query)
Diese Elemente repräsentieren bereits vom Broker verdichtete Handelsaktivitäten (oftmals auf Tagesbasis oder pro Trade).

- **Identifizierung:** Benötigt zwingend ein `symbol` und ein `tradeDate`. Fehlen diese, wird das Element übersprungen.
- **Asset Category Mapping:**
  - `STK` -> Equity (Aktien)
  - `OPT` -> Option
  - `FUT`, `FOP` -> Future
  - `CASH`, `FXCFD` -> Forex
  - `CRYPTO` -> Crypto
  - *Sonderregel `CASH`:* Forex-Konvertierungen (z.B. EUR in USD tauschen) werden **nicht** als Trade verbucht. Sie werden herausgefiltert. Fällt jedoch eine Kommission an, wird diese als `CashTransaction` vom Typ `FEE` erfasst (FX Conversion Commission).
- **Richtung & Menge:**
  - `quantity > 0` -> `LONG`
  - `quantity < 0` -> `SHORT`
  - Die im System gespeicherte Menge (`quantity`) ist immer der absolute (positive) Wert.
- **Preisfindung (3-Tier Fallback):**
  1. `tradePrice` Attribut.
  2. Falls 0: `tradeMoney` / `quantity` / `multiplier` (absolut).
  3. Falls 0: `cost` / `quantity` / `multiplier` (absolut).
  - Ist der Preis danach <= 0, wird die Ausführung ignoriert.
- **Kommissionsermittlung:**
  - Da IBKR Gebühren oft aufteilt oder nullt (z.B. `ibCommission="0"`, aber tatsächliche Drittanbieterkosten in `commission="-1.50"` stehen), nimmt der Parser das Maximum der absoluten Werte beider Felder: `max(abs(ibCommission), abs(commission))`. Dies verhindert "Double-Counting" und stellt sicher, dass Gebühren erfasst werden.
- **PnL (Profit and Loss) & Schließen:**
  - Das Feld `fifoPnlRealized` wird ausgewertet.
  - Ist der realisierte PnL **ungleich 0**, bedeutet dies, dass durch diese Zeile eine Position (teil)geschlossen wurde.
  - In diesem Fall wird das `closed_at` Datum auf `opened_at` + 1 Sekunde gesetzt (da IBKR pro Zeile nur einen Zeitstempel liefert, TradeJournal aber Start-/Enddatum erfordert).

### 2.2 `<Execution>` Elemente (Trade Confirmation)
Diese Elemente repräsentieren granulare Einzelausführungen einer Order.

- **Verarbeitung:** Ähnlich wie `<Trade>`, nutzt jedoch die Felder `execDate`, `execTime` und `price`.
- Es findet kein Fallback über `tradeMoney` oder PnL-Auswertung statt, da Einzelausführungen per Definition "nur" Ausführungen sind. Die eigentliche Ermittlung, ob ein Trade geschlossen wird, erfolgt später im Aggregator.
- **Kommissionsermittlung:** Identisch zur `Trade` Logik (`max(abs(...))`).

### 2.3 `<CashTransaction>` und `<TransactionTax>` Elemente
- **CashTransactions:** Dividenden, Zinsen, Brokergebühren (FEE), Einzahlungen (DEPOSIT) und Auszahlungen (WITHDRAWAL). Werden direkt anhand von Textmustern im `type`-Feld von IBKR den internen Kategorien zugeordnet.
- **TransactionTax:** Finanztransaktionssteuern (z.B. in Frankreich oder Italien) werden als `CashTransaction` vom Typ `FEE` verbucht, damit sie im Kassenbuch auftauchen und von der Gesamt-Performance abgezogen werden.

---

## 3. FIFO Aggregation & Trade-Zusammenfassung (`aggregator.py`)

Nachdem alle Ausführungen (sowohl aus `<Trade>` als auch aus `<Execution>`) als Liste von "Teil-Trades" (Executions) vorliegen, müssen Käufe und Verkäufe gematcht werden.

### 3.1 Warteschlangen-Prinzip (Queues)
Der Aggregator nutzt das Attribut `broker_conid` (die eindeutige IBKR Contract ID) oder ersatzweise `(symbol, asset_class)` als eindeutigen Schlüssel für ein Finanzinstrument.
Es existieren zwei Warteschlangen:
- **`open_lots`**: Hält alle Positionen, die geöffnet, aber noch nicht (vollständig) geschlossen wurden.
- **`orphaned_lots`**: Hält "verwaiste" Schließungen. Dies passiert, wenn ein Verkauf importiert wird, für den (noch) kein Kauf im System existiert (z.B. weil der Kauf in der Vergangenheit lag und die XML-Datei nur den aktuellen Monat abdeckt).

### 3.2 Matching-Regeln (First-In-First-Out)
Die Executions werden chronologisch abgearbeitet:

1. **Aufbau / Öffnen:**
   Trifft eine Ausführung ein, deren Richtung (`LONG`/`SHORT`) der Richtung der Warteschlange entspricht (oder die Queue ist leer), wird die Ausführung hinten an die `open_lots` Queue angehängt.

2. **Schließen / Gegengeschäft:**
   Besitzt die Ausführung die *entgegengesetzte* Richtung zur Warteschlange (z.B. Queue hält LONGs, aktuelle Ausführung ist SHORT), so wird die Order gegen die ältesten offenen Positionen (Lots) in der Queue "aufgefressen" (gematcht).

   - **Menge matchen:** Es wird ermittelt, wie viel von der aktuellen Ausführung gegen das älteste offene Lot gematcht werden kann (`min(open_lot.qty, execution.qty)`).
   - **Kommissionen splitten:** Die Kommissionen des öffnenden und des schließenden Lots werden proportional zur gematchten Menge aufgeteilt.
   - **Trade-Abschluss:** Ein fertiger `TradeCreate` (Round-Trip Trade) entsteht. Dieser erhält als Startdatum (`opened_at`) und Einstiegspreis (`entry_price`) die Werte des offenen Lots, sowie als Enddatum (`closed_at`) und Ausstiegspreis (`exit_price`) die Werte der schließenden Ausführung.
   - **Restmengen:** Ist die schließende Ausführung größer als das offene Lot, wird das offene Lot komplett geschlossen aus der Queue entfernt und die restliche Menge der schließenden Ausführung wird gegen das nächste offene Lot gematcht.

3. **Verwaiste Lots (Orphaned Lots):**
   Wenn eine schließende Ausführung nicht vollständig gegen offene Lots gematcht werden kann (weil die `open_lots` Queue leer ist), wird der verbleibende Rest in die `orphaned_lots` Queue gelegt. Diese werden später behandelt, falls über Kreuz-Imports (historische Dateien) noch passende Käufe nachgereicht werden.

### 3.3 Corporate Actions (Splits / Reverse-Splits)
Aktiensplits (Corporate Actions) werden chronologisch *während* der FIFO-Aggregation verarbeitet.
- Wenn das Datum einer Execution das Datum eines hinterlegten Splits überschreitet, wird die gesamte Queue der betroffenen Aktie angepasst.
- **Regel:** `lot.quantity *= ratio` und `lot.entry_price /= ratio`.
- Ändert der Split die IBKR Contract ID (`old_conid` -> `new_conid`), wird die Queue intern auf den neuen Schlüssel umgehängt.

### 3.4 Seed-Lots (Datenbank-Status)
Um historische Zusammenhänge zu wahren, kann der Aggregator mit `seed_open_lots` (bereits in der DB existierende offene Trades) vorbefüllt werden.
Wird ein Seed-Lot geschlossen, generiert der Aggregator ein Update (via `db_trade_id`), anstatt einen komplett neuen Trade zu persistieren.

### 3.5 Finale Validierung offener Positionen
Ganz am Ende prüft der Parser die offengebliebenen Trades in der `open_lots` Queue gegen den XML-Block `<OpenPosition>`.
- **Regel:** Wenn die XML-Datei `<OpenPosition>` Elemente enthält (und somit als vollumfänglicher Status-Report gilt), der offene Trade aber *nicht* als Contract ID in dieser Liste auftaucht, geht das System davon aus, dass die Position außerhalb eines regulären Trades geschlossen wurde (z.B. Ausbuchung, wertloser Verfall von Optionen).
- **Aktion:** Der Trade wird "force-closed". Das `closed_at` Datum wird auf `opened_at` + 1s gesetzt, der Exit-Preis entspricht dem Entry-Preis (0 PnL, reiner Gebührenverlust) und es wird eine Notiz angefügt: `[Force-closed: not in IBKR open positions]`.