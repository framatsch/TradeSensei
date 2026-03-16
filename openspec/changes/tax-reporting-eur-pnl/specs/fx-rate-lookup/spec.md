## ADDED Requirements

### Requirement: Tages-Wechselkurs abrufen
Das System SHALL den EUR/USD-Tageskurs für ein gegebenes Datum von der Deutschen Bundesbank Statistical Data Warehouse API abrufen. Als Kurs gilt der EZB-Referenzkurs (Statistikschlüssel `D.USD.EUR.SP00.A`).

#### Scenario: Kurs für Werktag vorhanden
- **WHEN** der Bundesbank-API-Aufruf für ein Datum (Werktag) erfolgreich ist
- **THEN** gibt die Funktion den EUR/USD-Rate als `Decimal` zurück

#### Scenario: Kein Kurs an Wochenende / Feiertag
- **WHEN** für das angefragte Datum kein Kurs vorhanden ist (Wochenende / Feiertag)
- **THEN** sucht das System den letzten verfügbaren Kurs bis maximal 3 Kalendertage zurück und gibt diesen zurück

#### Scenario: Kurs nicht abrufbar (API-Fehler / Timeout)
- **WHEN** die Bundesbank-API nicht erreichbar ist oder einen Fehler zurückgibt
- **THEN** gibt die Funktion `None` zurück (kein Exception-Raise; der Caller entscheidet über Fallback)

---

### Requirement: Wechselkurs cachen
Das System SHALL jeden erfolgreich abgerufenen Kurs in der Datenbanktabelle `fx_rates` speichern und bei erneutem Bedarf aus dem Cache lesen, ohne die API erneut aufzurufen.

#### Scenario: Cache-Hit
- **WHEN** ein Kurs für `(date, base="USD", quote="EUR")` bereits in `fx_rates` vorhanden ist
- **THEN** wird der gespeicherte Kurs zurückgegeben, ohne die Bundesbank-API aufzurufen

#### Scenario: Cache-Miss → Abruf und Speicherung
- **WHEN** kein Kurs für `(date, "USD", "EUR")` im Cache vorhanden ist
- **THEN** ruft das System die Bundesbank-API auf, speichert das Ergebnis in `fx_rates` und gibt den Kurs zurück

#### Scenario: Idempotentes Upsert
- **WHEN** derselbe Kurs für ein Datum zweimal gespeichert werden soll (z.B. Re-Import)
- **THEN** überschreibt das System den vorhandenen Eintrag ohne Fehler (Upsert-Semantik)
