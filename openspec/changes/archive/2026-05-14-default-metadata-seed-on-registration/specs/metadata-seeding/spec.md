## ADDED Requirements

### Requirement: Seed default taxonomies on registration
The system SHALL insert a curated set of user-scoped taxonomy records when a new account is created, covering Market Phase (checkins), Execution Quality (trades), and Strategy Category (playbooks scope → use `both` + name convention or `playbooks` when supported).

Each taxonomy record SHALL have:
- `name`: as specified below
- `scope`: `"checkins"` | `"trades"` | `"both"`
- `color_hex`: `#RRGGBB` as specified
- `icon_identifier`: Lucide-compatible string (e.g. `"trending-up"`)
- `user_id`: the newly created user's UUID

Default taxonomy seed set:

| Name | Scope | Color | Icon |
|------|-------|-------|------|
| Bullish | checkins | #22c55e | trending-up |
| Bearish | checkins | #ef4444 | trending-down |
| Sideways | checkins | #f59e0b | minus |
| Volatile | checkins | #a855f7 | activity |
| FOMO | trades | #ec4899 | alert-circle |
| Discipline | trades | #3b82f6 | shield |
| High Conviction | trades | #facc15 | zap |
| Breakout | both | #10b981 | arrow-up-right |
| Mean Reversion | both | #6366f1 | repeat |
| Momentum | both | #f97316 | rocket |
| Trend Following | both | #06b6d4 | trending-up |

#### Scenario: Registration triggers taxonomy seeding
- **WHEN** a new user account is created via `POST /auth/register` or OAuth flow
- **THEN** all 11 default taxonomy records are inserted linked to the new `user_id`

#### Scenario: Seeded tags visible in New Trade form
- **WHEN** user opens the New Trade form
- **THEN** the execution tags (FOMO, Discipline, High Conviction) and strategy tags (Breakout, Mean Reversion, Momentum, Trend Following) are available for selection

#### Scenario: Seeded tags visible in New Check-in form
- **WHEN** user opens the New Check-in form
- **THEN** the market phase tags (Bullish, Bearish, Sideways, Volatile) are available for selection

---

### Requirement: Seed default annotation definitions on registration
The system SHALL insert a curated set of user-scoped annotation definition records when a new account is created, covering psychological and execution metrics.

Default annotation definition seed set:

| Name | Type | Scope | scale_labels | Icon |
|------|------|-------|--------------|------|
| Mood Level | int | checkins | `{"min":1,"max":10}` | smile |
| Focus | int | checkins | `{"min":1,"max":10}` | target |
| Rule Followed | bool | trades | `{}` | check-square |
| Setup Quality | string_enum | trades | `{"options":["A+","B","C"]}` | award |

#### Scenario: Registration triggers annotation seeding
- **WHEN** a new user account is created
- **THEN** all 4 default annotation definition records are inserted linked to the new `user_id`

#### Scenario: Seeded metrics visible in New Check-in form
- **WHEN** user opens the New Check-in form
- **THEN** Mood Level and Focus annotation fields are available for input

#### Scenario: Seeded metrics visible in New Trade form
- **WHEN** user opens the New Trade form
- **THEN** Rule Followed (checkbox) and Setup Quality (A+/B/C selector) annotation fields are available for input

---

### Requirement: Idempotent seeding
The system SHALL NOT create duplicate records if the seeding function is called more than once for the same `user_id`.

The unique constraint `(user_id, name, scope)` on both tables SHALL enforce this at the database level. The seeding function SHALL handle `UniqueViolation` exceptions gracefully (log and continue) rather than raising.

#### Scenario: Duplicate registration hook call
- **WHEN** seeding is triggered a second time for an existing `user_id`
- **THEN** no new records are created and the operation completes without error

#### Scenario: Unique constraint on existing seed name
- **WHEN** a taxonomy with the same `(user_id, name, scope)` already exists
- **THEN** the insert is skipped and the existing record is preserved

---

### Requirement: Non-blocking seeding failure
Seeding failures SHALL NOT block user account creation. If any seed insert fails (beyond uniqueness), the error SHALL be logged and an audit event `metadata.seeding.failed` SHALL be emitted with `user_id` only.

#### Scenario: Seed fails with unexpected DB error
- **WHEN** an unexpected database error occurs during seeding
- **THEN** the user account is successfully created and returned
- **THEN** the error is logged with `logger.error()` including the user_id
- **THEN** audit event `metadata.seeding.failed` is emitted with `user_id`

---

## UI Mockup

### New Trade Form — Annotation & Tag Section

```
┌─────────────────────────────────────────────────┐
│ New Trade                                       │
├─────────────────────────────────────────────────┤
│ Tags                                            │
│  ┌──────────┐ ┌────────────┐ ┌────────────────┐│
│  │  FOMO    │ │ Discipline │ │ High Conviction ││
│  │ 🔴 #ec4899│ │ 🔵 #3b82f6 │ │ 🟡 #facc15     ││
│  └──────────┘ └────────────┘ └────────────────┘│
│  ┌──────────┐ ┌──────────────┐ ┌──────────────┐│
│  │ Breakout │ │ Mean Revers. │ │  Momentum    ││
│  └──────────┘ └──────────────┘ └──────────────┘│
│                                                 │
│ Annotations                                     │
│  Rule Followed:  [ ] (checkbox)                 │
│  Setup Quality:  [A+] [B] [C]  (chips/buttons)  │
└─────────────────────────────────────────────────┘
```

### New Check-in Form — Annotation & Tag Section

```
┌─────────────────────────────────────────────────┐
│ New Check-in                                    │
├─────────────────────────────────────────────────┤
│ Market Phase                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────┐│
│  │ Bullish  │ │ Bearish  │ │ Sideways │ │Volat││
│  │ 🟢#22c55e│ │ 🔴#ef4444│ │ 🟡#f59e0b│ │ 🟣  ││
│  └──────────┘ └──────────┘ └──────────┘ └─────┘│
│                                                 │
│ Annotations                                     │
│  Mood Level:  [━━━━●━━━━] 7/10  (slider)        │
│  Focus:       [━━━━━━●━━] 8/10  (slider)        │
└─────────────────────────────────────────────────┘
```
