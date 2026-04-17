# Playwright Testplan - Trade Sensei Basis-Funktionalität

## Übersicht

Dieser Testplan deckt die Basis-Funktionalität der Trade Sensei Anwendung ab. Die Tests werden mit Playwright ausgeführt und sollen als End-to-End-Tests die kritischen User Flows verifizieren.

## Voraussetzungen

- Frontend läuft auf `http://localhost:3000`
- Backend läuft auf `http://localhost:8000`
- Test-Datenbank ist eingerichtet (oder frische DB via Docker Compose)

---

## Test-Suite 1: Authentifizierung

### TC-001: Erfolgreicher Login

**Beschreibung**: Benutzer kann sich mit gültigen Credentials anmelden

**Vorbedingungen**:
- Benutzer ist nicht eingeloggt
- Benutzer-Account existiert in der Datenbank

**Schritte**:
1. Navigiere zu `/login`
2. Fülle Username-Feld mit gültigem Wert (z.B. `testuser`)
3. Fülle Password-Feld mit gültigem Passwort
4. Klicke "Sign In" Button
5. Warte auf Weiterleitung zum Dashboard

**Erwartetes Ergebnis**:
- Erfolgreiche Weiterleitung zu `/dashboard`
- Keine Fehlermeldung sichtbar
- Benutzer ist eingeloggt (Token im localStorage)

---

### TC-002: Fehlgeschlagener Login (falsches Passwort)

**Beschreibung**: System zeigt Fehlermeldung bei falschen Credentials

**Vorbedingungen**:
- Benutzer ist nicht eingeloggt
- Benutzer-Account existiert

**Schritte**:
1. Navigiere zu `/login`
2. Fülle Username-Feld mit existierendem Benutzer
3. Fülle Password-Feld mit falschem Passwort
4. Klicke "Sign In" Button

**Erwartetes Ergebnis**:
- Fehlermeldung wird angezeigt: "Login failed. Please check your credentials."
- Benutzer bleibt auf Login-Seite
- Keine Weiterleitung zum Dashboard

---

### TC-003: Fehlgeschlagener Login (leere Felder)

**Beschreibung**: Formular-Validierung verhindert leere Eingaben

**Vorbedingungen**:
- Benutzer ist nicht eingeloggt

**Schritte**:
1. Navigiere zu `/login`
2. Klicke "Sign In" Button ohne Eingaben

**Erwartetes Ergebnis**:
- HTML5 Form-Validierung zeigt Fehler
- Submit wird blockiert (oder Browser-Fehler)

---

### TC-004: Erfolgreiche Registrierung

**Beschreibung**: Neuer Benutzer kann Account erstellen

**Vorbedingungen**:
- Benutzer ist nicht eingeloggt
- Kein Account mit gewähltem Username existiert

**Schritte**:
1. Navigiere zu `/register`
2. Fülle Username-Feld (z.B. `newuser123`)
3. Fülle Email-Feld (z.B. `newuser123@example.com`)
4. Fülle Password-Feld mit gültigem Passwort
5. Fülle Password confirmation-Feld mit gleichem Passwort
6. Klicke "Create Account" Button
7. Warte auf Weiterleitung

**Erwartetes Ergebnis**:
- Erfolgreiche Weiterleitung zu `/dashboard` oder `/login`
- Account wurde in DB erstellt

---

### TC-005: Registrierung - Passwort stimmt nicht überein

**Beschreibung**: Validierung bei mismatched Passwörtern

**Vorbedingungen**:
- Benutzer ist nicht eingeloggt

**Schritte**:
1. Navigiere zu `/register`
2. Fülle alle Pflichtfelder aus
3. Fülle Password und Password confirmation mit unterschiedlichen Werten
4. Klicke "Create Account" Button

**Erwartetes Ergebnis**:
- Fehlermeldung wird angezeigt
- Kein Account wird erstellt

---

### TC-006: Navigation zwischen Login und Register

**Beschreibung**: Links zwischen Auth-Seiten funktionieren

**Vorbedingungen**:
- Benutzer ist nicht eingeloggt

**Schritte**:
1. Navigiere zu `/login`
2. Klicke "Create one" Link
3. Prüfe URL und Inhalt
4. Klicke "Sign in" Link
5. Prüfe Rückkehr zur Login-Seite

**Erwartetes Ergebnis**:
- Klick auf "Create one" führt zu `/register`
- Klick auf "Sign in" führt zu `/login`

---

## Test-Suite 2: Dashboard

### TC-010: Dashboard lädt mit Metriken

**Beschreibung**: Eingeloggter Benutzer sieht Dashboard mit Metriken

**Vorbedingungen**:
- Benutzer ist eingeloggt
- Datenbank enthält Trades

**Schritte**:
1. Login als Benutzer mit Trades
2. Warte bis Dashboard vollständig geladen

**Erwartetes Ergebnis**:
- Seite zeigt "Overview" Titel
- MetricsCards werden angezeigt (Win Rate, Profit Factor, etc.)
- Equity Curve Chart ist sichtbar
- Drawdown Chart ist sichtbar
- Keine Fehlermeldungen

---

### TC-011: Dashboard "No trades yet" Zustand

**Beschreibung**: Leeres Dashboard zeigt hilfreiche Nachricht

**Vorbedingungen**:
- Benutzer ist eingeloggt
- Keine Trades in der Datenbank

**Schritte**:
1. Login als frischer Benutzer ohne Trades
2. Warte bis Dashboard geladen

**Erwartetes Ergebnis**:
- Nachricht "No trades yet" wird angezeigt
- Link zur Import-Seite ist sichtbar und funktioniert

---

### TC-012: Dashboard Fehlerzustand + Retry

**Beschreibung**: Fehlerbehandlung bei API-Fehlern

**Vorbedingungen**:
- Benutzer ist eingeloggt

**Schritte**:
1. Simuliere API-Fehler (z.B. durch falsches Token oder Server-Fehler)
2. Prüfe Fehlermeldung
3. Klicke "Retry" Button

**Erwartetes Ergebnis**:
- Fehlermeldung wird angezeigt
- Retry-Button ist sichtbar
- Klick auf Retry versucht erneutes Laden

---

## Test-Suite 3: Navigation & Layout

### TC-020: Haupt-Navigation funktioniert

**Beschreibung**: Navigation zwischen Hauptseiten

**Vorbedingungen**:
- Benutzer ist eingeloggt

**Schritte**:
1. Klicke auf "Trades" im Navigation Menu
2. Warte bis Trades-Seite lädt
3. Prüfe URL und Inhalt
4. Klicke auf "Playbooks" im Menu
5. Prüfe URL und Inhalt
6. Klicke auf "Tags" im Menu
7. Prüfe URL und Inhalt
8. Klicke auf "Import" im Menu
9. Prüfe URL und Inhalt

**Erwartetes Ergebnis**:
- Alle Navigation-Links funktionieren
- Richtige Seiten werden geladen

---

### TC-021: Logout funktioniert

**Beschreibung**: Benutzer kann sich ausloggen

**Vorbedingungen**:
- Benutzer ist eingeloggt

**Schritte**:
1. Klicke auf Logout (z.B. via Header/Profile Menu)
2. Warte auf Weiterleitung

**Erwartetes Ergebnis**:
- Token wird aus localStorage entfernt
- Benutzer wird zu `/login` weitergeleitet
- Zugang zu `/dashboard` ohne Login nicht mehr möglich

---

## Test-Suite 4: Trades Liste

### TC-030: Trades-Tabelle wird geladen

**Beschreibung**: Trade-Liste zeigt existierende Trades

**Vorbedingungen**:
- Benutzer ist eingeloggt
- Datenbank enthält Trades

**Schritte**:
1. Navigiere zu `/dashboard/trades`
2. Warte bis Tabelle geladen

**Erwartetes Ergebnis**:
- Trade-Tabelle wird angezeigt
- Trades werden in Tabelle aufgelistet
- Spalten sind sichtbar (Symbol, Direction, P&L, etc.)

---

## Test-Suite 5: Import (falls verfügbar)

### TC-040: Import-Seite ist zugänglich

**Beschreibung**: Import-Funktionalität ist erreichbar

**Vorbedingungen**:
- Benutzer ist eingeloggt

**Schritte**:
1. Navigiere zu `/dashboard/import`
2. Warte bis Seite lädt

**Erwartetes Ergebnis**:
- Import-Formular wird angezeigt
- File-Upload Bereich ist sichtbar

---

## Test-Ausführung

### Lokale Ausführung

```bash
# Dev-Server starten (in separatem Terminal)
cd /home/scheffold/work/tradesensei
docker compose up -d

# Tests ausführen
npx playwright test --ui
```

### Headless Ausführung

```bash
npx playwright test
```

### Bestimmte Suite ausführen

```bash
# Nur Auth-Tests
npx playwright test --grep "auth|login|register"

# Nur Dashboard
npx playwright test --grep "Dashboard"
```

---

## Erwartete Test-Dateien Struktur

```
frontend/tests/
├── auth/
│   ├── login.spec.ts
│   ├── register.spec.ts
│   └── logout.spec.ts
├── dashboard/
│   ├── dashboard.spec.ts
│   └── dashboard-empty.spec.ts
├── navigation/
│   └── main-nav.spec.ts
├── trades/
│   └── trades-list.spec.ts
└── import/
    └── import-page.spec.ts
```

---

## Nächste Schritte

1. **Dieser Plan validieren** - Stimmen die Testfälle mit der erwarteten Funktionalität überein?
2. **Dev-Environment starten** - Docker Compose starten
3. **Tests implementieren** - Playwright Tests schreiben
4. **Tests ausführen** - Erste Test-Runde durchführen
5. **Ergebnisse evaluieren** - Fehler analysieren und beheben
