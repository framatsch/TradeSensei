Bei Option 1 mit has_conflict = true:
Monat 1: User erstellt MANUAL
Trade: MANUAL (100 shares, kein TX-Link)
has_conflict: false
Monat 2: Erster Flex Query Import
TX123 gefunden → nicht in DB → wird importiert
Trade: MANUAL (100) + IMPORTED TX123 (100)
→ has_conflict = true (wegen Duplicate Detection)
Import Summary: "1 trade flagged with conflict"
Monat 3: Zweiter Flex Query Import
TX123 gefunden → bereits in DB (IMPORTED existiert) → SKIP
Trade: MANUAL (100) + IMPORTED TX123 (100) (unverändert)
→ has_conflict = true (bleibt gesetzt)
Import Summary: "TX123 skipped (already imported)"
→ has_conflict bleibt true bis User manuell aufräumt!
Das Problem:
