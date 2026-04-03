## Context

Das aktuelle System importiert Broker-Ausführungen (Executions) und aggregiert diese per FIFO zu geschlossenen Round-Trip Trades. Die Aggregation basiert auf dem Schlüssel `(symbol, broker_conid, asset_class)`. Bei Aktiensplits (und Reverse Splits) ändert sich bei IBKR die `conid` des Instruments, weshalb Kauf- und Verkaufsausführungen, die den Split "überspannen", nicht mehr als zusammengehörig erkannt werden. Das führt zu dauerhaft "offenen" Zombietrades im Journal.

Die aktuelle Workaround-Lösung gleicht zwar nach dem Import die noch offenen Trades gegen den `<OpenPosition>`-Block der XML-Datei ab und schließt sie "zwangsweise" — aber ohne korrekte Preise, Stückzahlen und PnL. Das ist mathematisch nicht korrekt.

Der User kann seine Daten neu importieren, was uns erlaubt, die Architektur sauber aufzubauen, ohne Legacy-Kompatibilität zu berücksichtigen.

## Goals / Non-Goals

**Goals:**
- Mathematisch korrekte Berechnung von Stückzahl und Einstiegspreis für Trades, die einen Split überspannen.
- Unterstützung von Fractional Shares (Dezimalstückzahlen) bei Split-Berechnungen.
- Manuelle Pflege von Split-Events durch den User über eine UI.
- ID-Mapping (old_conid → new_conid) für IBKR-spezifische Conid-Wechsel bei Splits.
- Schutz manuell korrigierter Trades vor Überschreiben durch zukünftige Imports.

**Non-Goals:**
- Automatische Erkennung von Splits aus Broker-Daten (Corporate Actions in IBKR XML/CSV) — das wäre Phase 2.
- Dividend-Adjustments oder andere Corporate Actions außer Splits/Reverse Splits.
- Historische Umrechnung bereits gespeicherter Trades beim Anlegen eines neuen Split-Events (nur beim nächsten Re-Import wird korrekt aggregiert).

## Decisions

### 1. Separate `corporate_actions` Tabelle statt Split-Felder im `Trade` Model

**Entscheidung:** Ein neues SQLAlchemy Model `CorporateAction` mit eigener Tabelle.

**Rationale:** Splits sind keine Eigenschaft eines einzelnen Trades, sondern globale Events für ein Symbol zu einem Zeitpunkt. Wenn wir den Split am Symbol-Level speichern, müssen wir ihn nur einmal eingeben — und er gilt automatisch für alle Trades dieses Symbols in dem Zeitraum. Hätten wir ihn pro Trade gespeichert, müsste der User jeden betroffenen Trade einzeln korrigieren.

**Alternative:** Split-Felder direkt im Trade Model (`split_ratio`, `split_date`). Abgelehnt, da redundant und fehleranfällig.

### 2. Split-Aware Aggregator: Event-Stream-Ansatz

**Entscheidung:** Die Funktion `aggregate_executions_fifo` bekommt zusätzlich eine Liste von `CorporateAction`-Objekten übergeben. Intern werden Executions und Corporate Actions zu einem chronologischen Event-Stream zusammengefasst und sequenziell abgearbeitet.

**Verarbeitung eines Split-Events:** Wenn ein Split-Event chronologisch "eintrifft" (d.h. sein Datum liegt zwischen zwei Executions), werden alle aktuell in der `open_lots`-Queue befindlichen Lots für das betroffene Symbol umgerechnet:
- `quantity = quantity * ratio`
- `entry_price = entry_price / ratio`

Außerdem wird der interne Queue-Key von `(symbol, old_conid, asset_class)` auf `(symbol, new_conid, asset_class)` umgeschlüsselt, damit der spätere Verkauf (der mit der neuen conid kommt) den korrekten Lot findet.

**Rationale:** Dieser Ansatz ist präzise (der Split wird exakt zum richtigen Zeitpunkt angewendet), erweiterbar (andere Corporate Action-Typen könnten ähnlich implementiert werden) und testbar (reine Funktion mit definierten Inputs).

**Alternative:** Normalisierung aller Trades nachträglich nach dem Import. Abgelehnt, weil es den PnL durch Rundungsfehler verzerren kann und die Originalwerte in der DB gespeichert würden (die dann nicht mehr zum Broker-Statement passen).

### 3. `is_manually_edited` Flag im `Trade` Model

**Entscheidung:** Das `Trade`-Model bekommt ein Boolean-Feld `is_manually_edited` (Default: `False`). Der `ImportService` überspringt beim Re-Import Trades, für die dieses Flag gesetzt ist (Matching über `broker_order_id` oder `broker_conid` + `opened_at`).

**Rationale:** Gibt dem User die Kontrolle, einzelne Trades "einzufrieren", ohne dass der nächste Import die Korrekturen wieder zunichte macht.

**Alternative:** Versionierung von Trades (jede Import-Version als separater Record). Abgelehnt als zu komplex für den aktuellen Scope.

### 4. Ratio-Eingabe in der UI als "Von X zu Y"-Verhältnis

**Entscheidung:** In der UI gibt der User nicht direkt den Dezimal-Ratio ein (z.B. `0.05`), sondern ein menschenlesbares Verhältnis: "Von 20 Aktien → zu 1 Aktie" (= Reverse Split 1:20). Das Frontend errechnet daraus den Ratio (`1/20 = 0.05`) und schickt nur den Decimal-Ratio an die API.

**Rationale:** `0.05` ist fehleranfällig und unintuitiv. "20:1" oder "1:20" ist das, was in Finanznachrichten kommuniziert wird.

### 5. Split-Events sind user-scoped

**Entscheidung:** Jede `CorporateAction` hat eine `user_id` Foreign Key. Es gibt keine globale, system-weite Split-Datenbank.

**Rationale:** Zwei User könnten dieselbe Aktie zu unterschiedlichen Zeiten gehalten haben, mit unterschiedlicher Relevanz. Außerdem vermeiden wir falsche Positive für User, die nie OTLK gehalten haben. Hält sich der Aufwand für den User in Grenzen, da er ohnehin nur wenige Split-Events pro Jahr eingibt.

## Risks / Trade-offs

- **[Risiko] User vergisst einen Split einzutragen → Trade bleibt falsch offen.** Mitigation: Die Force-Close-Logik (über `<OpenPosition>`) bleibt als letzter Fallback erhalten. Wir erweitern die Import-Warnungen um einen expliziten Hinweis "Möglicher Split erkannt (Stückzahl-Diskrepanz)" um den User auf das Problem aufmerksam zu machen.
- **[Risiko] User gibt falschen Ratio oder falsches Datum ein → alle Trades für das Symbol werden falsch berechnet.** Mitigation: UI zeigt eine Vorschau ("Dieses Split-Event betrifft X offene Trades"), bevor es gespeichert wird. Außerdem ist ein Re-Import jederzeit möglich.
- **[Trade-off] Nur korrekter PnL nach Re-Import, nicht sofort.** Das Anlegen eines neuen Split-Events im UI korrigiert keine bereits gespeicherten Trades rückwirkend. Der User muss danach einen Re-Import durchführen. Wir kommunizieren das klar in der UI.
- **[Risiko] Rundungsfehler bei Dezimal-Arithmetic.** Mitigation: `Decimal`-Typ durchgehend, kein `float`. Python's `decimal`-Modul ist exakt für diese Anwendungsfälle.

## Migration Plan

1. Neue Alembic Migration generieren: Tabelle `corporate_actions` + Feld `is_manually_edited` in `trades`.
2. Da der User die Daten re-importiert, ist kein Datenmigrations-Skript nötig — nur Schema-Migration.
3. Rollback: Alembic `downgrade -1` entfernt die neue Tabelle und das neue Feld.

## Open Questions

- Soll es in Zukunft eine automatische Erkennung von Splits aus IBKR Corporate-Action-Einträgen in der XML geben? → Out of Scope für dieses Change, aber die Architektur ist darauf vorbereitet (die `CorporateAction`-Tabelle ist dafür schon die richtige Basis).
