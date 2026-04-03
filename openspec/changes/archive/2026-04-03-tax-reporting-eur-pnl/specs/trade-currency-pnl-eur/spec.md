## ADDED Requirements

### Requirement: Trade speichert Handelswährung
Das `Trade`-Modell SHALL ein neues nullable Feld `currency VARCHAR(3)` (ISO-4217) besitzen, das die Denominierungswährung des Trades angibt (z.B. `"USD"`).

#### Scenario: Währung beim Import gesetzt
- **WHEN** ein Trade via IBKR- oder Schwab-Import erstellt wird
- **THEN** ist `trade.currency` auf `"USD"` gesetzt

#### Scenario: Manuelle Trades ohne Währung
- **WHEN** ein Trade manuell via `POST /trades` ohne `currency`-Feld erstellt wird
- **THEN** ist `trade.currency` `null` (keine Pflichtangabe)

---

### Requirement: Trade speichert realisierten P&L in EUR
Das `Trade`-Modell SHALL ein neues nullable Feld `pnl_eur NUMERIC(18,8)` besitzen. Es enthält den realisierten Gewinn/Verlust in Euro, umgerechnet mit dem amtlichen EUR/USD-Tageskurs zum Handelsdatum.

#### Scenario: pnl_eur bei geschlossenem Trade mit bekanntem Kurs
- **WHEN** ein Trade einen `pnl`-Wert hat und der EUR/USD-Kurs für das `closed_at`-Datum (oder `opened_at` als Fallback) bekannt ist
- **THEN** ist `pnl_eur = pnl / rate` (gerundet auf 2 Dezimalstellen)

#### Scenario: pnl_eur bei offenem Trade
- **WHEN** ein Trade `pnl = null` hat (offener Trade)
- **THEN** ist `pnl_eur = null`

#### Scenario: pnl_eur bei nicht verfügbarem Kurs
- **WHEN** der EUR/USD-Kurs für das Handelsdatum nicht abrufbar ist
- **THEN** ist `pnl_eur = null` und ein Warnungs-Eintrag erscheint in `ImportResult.warnings`

---

### Requirement: TradeRead-Response enthält EUR-Felder
Die `TradeRead`-Schema SHALL die Felder `currency: str | None` und `pnl_eur: Decimal | None` enthalten.

#### Scenario: Felder in API-Response sichtbar
- **WHEN** `GET /trades/{id}` aufgerufen wird
- **THEN** enthält die Response `currency` und `pnl_eur` (ggf. `null`)
