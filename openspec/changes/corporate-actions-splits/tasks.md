## 1. Datenbank & Models (Backend)

- [x] 1.1 Neues SQLAlchemy Model `CorporateAction` in `backend/app/models/corporate_action.py` erstellen (Felder: `id`, `user_id`, `symbol`, `date`, `ratio`, `old_conid`, `new_conid`, `created_at`, `updated_at`)
- [x] 1.2 Model `Trade` in `backend/app/models/trade.py` um das Feld `is_manually_edited` (Boolean, Default: `False`) erweitern
- [x] 1.3 `CorporateAction` Model in `backend/app/models/__init__.py` registrieren
- [x] 1.4 Alembic Migration generieren und reviewen: neue Tabelle `corporate_actions` + neues Feld `is_manually_edited` in `trades`
- [x] 1.5 Migration gegen die lokale Test-DB anwenden und verifizieren

## 2. Pydantic Schemas (Backend)

- [x] 2.1 Neue Schemadatei `backend/app/schemas/corporate_action.py` mit `CorporateActionCreate`, `CorporateActionUpdate`, `CorporateActionRead` erstellen
- [x] 2.2 `TradeCreate` Schema in `backend/app/schemas/trade.py` um `is_manually_edited` erweitern (optional, Default `False`)

## 3. Repository & Service (Backend)

- [x] 3.1 Neues Repository `backend/app/repositories/corporate_action_repository.py` mit `list_by_user`, `get_by_id`, `create`, `update`, `delete` implementieren
- [x] 3.2 Neuen Service `backend/app/services/corporate_action_service.py` mit CRUD-Logik implementieren (inkl. Ownership-Prüfung bei `update`/`delete`)

## 4. Split-Aware Aggregator (Backend)

- [x] 4.1 `aggregate_executions_fifo` in `backend/app/utils/parsers/aggregator.py` refaktorieren: Parameter `corporate_actions: list[CorporateAction] | None = None` hinzufügen
- [x] 4.2 Event-Stream-Logik implementieren: Corporate Actions und Executions chronologisch verarbeiten; bei Split-Event alle betroffenen `open_lots` umrechnen (`qty * ratio`, `price / ratio`)
- [x] 4.3 `old_conid` → `new_conid` Queue-Key-Umschlüsselung im Aggregator implementieren
- [x] 4.4 Warnung bei möglichem unregistriertem Split implementieren (Stückzahl-Diskrepanz beim Matching)
- [x] 4.5 Unit-Tests in `backend/tests/test_aggregator.py` ergänzen: 2:1 Forward Split, 1:20 Reverse Split (OTLK-Szenario), Fractional Shares, rückwärtskompatible Ausführung ohne `corporate_actions`

## 5. Import Service Update (Backend)

- [x] 5.1 `ImportService.import_file` in `backend/app/services/import_service.py` so erweitern, dass es vor dem Parsen alle `CorporateAction`s des Users aus der DB lädt und an den Aggregator weitergibt
- [x] 5.2 Logik zum Überspringen von Trades mit `is_manually_edited = True` beim Re-Import implementieren (Matching über `broker_conid` + `opened_at`)

## 6. API Router (Backend)

- [x] 6.1 Neuen FastAPI Router `backend/app/api/v1/corporate_actions.py` mit Endpunkten `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}` implementieren
- [x] 6.2 Router in `backend/app/api/v1/router.py` unter dem Prefix `/corporate-actions` registrieren
- [x] 6.3 OpenAPI Annotations und Pydantic Field Descriptions vollständig ergänzen

## 7. Tests Backend

- [x] 7.1 Unit-Tests für `CorporateActionService` in `backend/tests/test_corporate_action_service.py` schreiben (CRUD + Ownership)
- [x] 7.2 API-Tests für den Corporate Actions Router in `backend/tests/test_corporate_actions_api.py` schreiben (alle 4 Endpunkte, Fehlerszenarien)
- [x] 7.3 Bestehende Import-Tests in `backend/tests/test_import.py` um Split-Szenario erweitern

## 8. OpenAPI Sync & Frontend Grundlagen

- [x] 8.1 `openapi-sync` ausführen, um den TypeScript API Client neu zu generieren
- [x] 8.2 React Query Hooks für Corporate Actions (`useListCorporateActions`, `useCreateCorporateAction`, `useUpdateCorporateAction`, `useDeleteCorporateAction`) anlegen

## 9. Frontend: Settings-Seite Corporate Actions

- [x] 9.1 Neue Seite `frontend/app/settings/corporate-actions/page.tsx` erstellen
- [x] 9.2 Tabelle zur Auflistung aller Corporate Actions mit Spalten: Symbol, Datum, Ratio (menschenlesbar "1:20"), Old Conid, New Conid, Aktionen (Edit/Delete) implementieren
- [x] 9.3 "Add Corporate Action"-Modal mit Formularfeldern implementieren: Symbol, Datum, "Before"-Zahl, "After"-Zahl (Ratio wird im Frontend berechnet: `after / before`), Old Conid (optional), New Conid (optional)
- [x] 9.4 "Edit"-Funktionalität im Modal implementieren (Formular mit bestehenden Werten befüllen, `PUT`-Call)
- [x] 9.5 "Delete"-Bestätigungsdialog und `DELETE`-Call implementieren
- [x] 9.6 Link zur neuen Seite in der Settings-Navigation ergänzen

## 10. Frontend: Trade Detail — Manuelles Edit Flag

- [x] 10.1 In der Trade-Detailansicht ein visuelles Indikator-Label "Manually Edited" anzeigen, wenn `is_manually_edited = true`
- [x] 10.2 Beim Speichern eines manuellen Trade-Edits via `PUT /trades/{id}` das Flag `is_manually_edited = true` mitschicken

## 11. Lint, Typecheck & Abschluss

- [x] 11.1 `lint-check` Skill ausführen (ruff + mypy --strict) und alle Fehler beheben
- [x] 11.2 Alle neuen und bestehenden Unit-Tests ausführen (`unit-test` Skill) — Ziel: grüner Build
- [x] 11.3 Lokale Entwicklungsumgebung hochfahren (`deploy-local` Skill) und manuellen End-to-End-Test durchführen: Split anlegen → Import → Trade prüfen
