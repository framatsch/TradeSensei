## Context

After implementing soft-delete (Change 1) and Fresh Start import (Change 2), journaling data (TradeNotes, TradeTags, TradePlaybooks) becomes orphaned when trades are permanently deleted. The FK constraint `ON DELETE SET NULL` ensures data isn't lost, but creates a new challenge: how to reconnect orphaned entries to re-imported trades.

### Current State
- TradeNotes, TradeTags, TradePlaybooks have FK: trade_id REFERENCES trades(id) ON DELETE SET NULL
- When trade deleted → trade_id = NULL (orphaned)
- Orphaned entries remain in database with no link to trades
- No mechanism exists to reconnect orphaned data

### User Impact
- High-value user input (notes, analysis, lessons learned) disconnected from trades
- After Fresh Start, 100+ orphaned entries may accumulate
- Manual re-linking is tedious and error-prone
- Users may give up and delete orphaned data (losing valuable insights)

## Goals / Non-Goals

**Goals:**
- Automatically reconnect orphaned journaling to re-imported trades (best-effort heuristic)
- Provide UI for manual review and linking
- Allow bulk operations (accept all, delete all, export)
- Preserve orphaned data until user explicitly deletes
- Add metadata to journal entries for better matching (symbol, dates)

**Non-Goals:**
- 100% accurate auto-matching (heuristic, not perfect)
- ML/AI-based matching (future enhancement)
- Conflict resolution (multiple orphaned notes → same trade)
- Undo/revert auto-matching

## Decisions

### Decision 1: Add Metadata to Journaling Tables

**Rationale:** Without symbol and date info, orphaned entries can't be matched. Adding these fields enables heuristic matching after orphaning.

**Schema Changes:**
```sql
ALTER TABLE trade_notes ADD COLUMN symbol VARCHAR(20);
ALTER TABLE trade_notes ADD COLUMN opened_at TIMESTAMP;
ALTER TABLE trade_notes ADD COLUMN closed_at TIMESTAMP;

-- Repeat for trade_tags, trade_playbooks
```

**Backfill Migration:**
```sql
-- Backfill existing rows (where trade_id not NULL)
UPDATE trade_notes 
SET symbol = trades.symbol,
    opened_at = trades.opened_at,
    closed_at = trades.closed_at
FROM trades
WHERE trade_notes.trade_id = trades.id;
```

**Why Add Metadata:**
- Orphaned entries need context for matching
- Symbol + date range uniquely identify most trades
- Small storage cost (~30 bytes per row)

**Alternative considered:** Query trade history from BrokerRawTransactions
- Rejected: Complex, BrokerRawTransactions may not have all trades (manual trades)

### Decision 2: Auto-Matching Heuristic (Symbol + Time Window)

**Rationale:** Simple heuristic covers 80%+ of cases. Symbol + time proximity is strong signal.

**Matching Algorithm:**
```python
def find_match_for_orphaned_note(note: TradeNote, trades: List[Trade]) -> Optional[Match]:
    candidates = []
    
    for trade in trades:
        if trade.symbol != note.symbol:
            continue  # Must match symbol
        
        # Time proximity score
        time_diff = abs((trade.opened_at - note.opened_at).total_seconds())
        
        if time_diff <= 3600:  # ±1 hour
            confidence = 100  # Exact match
        elif time_diff <= 7200:  # ±2 hours
            confidence = 80  # Close match
        elif time_diff <= 86400:  # ±1 day
            confidence = 50  # Possible match
        else:
            continue  # Too far apart
        
        candidates.append(Match(trade=trade, confidence=confidence))
    
    if not candidates:
        return None  # No match found
    
    # Return highest confidence match
    return max(candidates, key=lambda m: m.confidence)
```

**Confidence Thresholds:**
- **100%**: Symbol match + time within ±1 hour → Auto-link (safe)
- **80-99%**: Symbol match + time within ±2 hours → Suggest, require user confirmation
- **50-79%**: Symbol match + time within ±1 day → Flag for manual review
- **<50%**: Too uncertain, don't suggest

**Alternative considered:** Match by P&L or trade characteristics
- Rejected: P&L may differ after re-import (different FIFO order)
- Rejected: More complex, diminishing returns

**Alternative considered:** Always require manual confirmation
- Rejected: Tedious for users with 100+ orphaned entries

### Decision 3: Auto-Matching Runs After Import (Not Continuous)

**Rationale:** Auto-matching is expensive (O(n×m) comparisons). Run once after import, not on every trade create.

**Implementation:**
```python
async def fresh_start_import(file, db):
    # Delete phase
    await delete_all_data(db)
    
    # Import phase
    result = await process_import(file, db)
    
    # Auto-matching phase (NEW)
    orphaned_notes = await get_orphaned_notes(db)
    trades = await get_all_trades(db)
    
    matches = []
    for note in orphaned_notes:
        match = find_match_for_orphaned_note(note, trades)
        if match and match.confidence >= 100:
            # Auto-link high-confidence matches
            note.trade_id = match.trade.id
            matches.append(match)
    
    await db.commit()
    
    result.auto_matched = len(matches)
    return result
```

**Alternative considered:** Run auto-matching on every trade creation
- Rejected: Performance overhead, unnecessary

**Alternative considered:** Background job runs auto-matching periodically
- Rejected: Over-engineering, imports are infrequent

### Decision 4: Orphaned Review UI as Separate Page

**Rationale:** Orphaned management is low-frequency task. Dedicated page keeps main UI clean.

**Navigation:**
```jsx
<Sidebar>
  <NavLink to="/trades">Trades</NavLink>
  <NavLink to="/playbooks">Playbooks</NavLink>
  {orphanedCount > 0 && (
    <NavLink to="/orphaned-journaling">
      Orphaned Entries
      <Badge variant="warning">{orphanedCount}</Badge>
    </NavLink>
  )}
</Sidebar>
```

**Alternative considered:** Show orphaned entries in main trade list
- Rejected: Clutters UI, orphaned entries have no trade to attach to

**Alternative considered:** Modal dialog on login if orphaned entries exist
- Rejected: Annoying, user may not be ready to deal with it

### Decision 5: Manual Linking via Search/Select

**Rationale:** User needs ability to correct auto-matching mistakes or link when auto-match fails.

**UI Flow:**
```jsx
<OrphanedEntryCard entry={note}>
  <Text>Note: "Great setup, waited for confirmation"</Text>
  <Text secondary>Original Trade: AAPL, 2024-03-15</Text>
  
  {suggestedMatch ? (
    <Alert info>
      Suggested: AAPL 2024-03-15 10:30-11:45
      Confidence: 85%
      <Button>Link to This Trade</Button>
    </Alert>
  ) : (
    <Text>No automatic match found</Text>
  )}
  
  <Button onClick={openManualLinkDialog}>
    Manually Link to Trade
  </Button>
  
  <Button variant="destructive">Delete</Button>
</OrphanedEntryCard>

<ManualLinkDialog>
  <SearchInput placeholder="Search by symbol or date..." />
  <TradeList>
    {filteredTrades.map(trade => (
      <TradeCard 
        key={trade.id}
        trade={trade}
        onClick={() => linkNoteToTrade(note.id, trade.id)}
      />
    ))}
  </TradeList>
</ManualLinkDialog>
```

**Alternative considered:** Dropdown of all trades
- Rejected: Hundreds of trades, dropdown is unwieldy

**Alternative considered:** Type trade ID manually
- Rejected: User doesn't know trade IDs

### Decision 6: Bulk Operations with Confirmation

**Rationale:** Users with 100+ orphaned entries need bulk operations. Confirmation prevents accidents.

**Operations:**

**Accept All High-Confidence:**
```python
@router.post("/journaling/orphaned/accept-matches")
async def accept_high_confidence_matches(
    confidence_threshold: int = 80,
    db: AsyncSession = Depends(get_db)
):
    orphaned = await get_orphaned_with_matches(db)
    linked_count = 0
    
    for entry in orphaned:
        if entry.suggested_match and entry.confidence >= confidence_threshold:
            entry.trade_id = entry.suggested_match.trade_id
            linked_count += 1
    
    await db.commit()
    return {"linked": linked_count}
```

**Delete All Orphaned:**
```python
@router.delete("/journaling/orphaned")
async def delete_all_orphaned(
    confirm: bool = Body(...),
    db: AsyncSession = Depends(get_db)
):
    if not confirm:
        raise HTTPException(400, "Must confirm deletion")
    
    deleted = await db.execute(
        delete(TradeNote).where(TradeNote.trade_id == None)
    )
    # Repeat for TradeTags, TradePlaybooks
    
    await db.commit()
    return {"deleted": deleted.rowcount}
```

**Export as JSON:**
```python
@router.get("/journaling/orphaned/export")
async def export_orphaned(db: AsyncSession = Depends(get_db)):
    orphaned = await get_orphaned(db)
    data = [
        {
            "type": "note",
            "content": note.content,
            "symbol": note.symbol,
            "opened_at": note.opened_at.isoformat(),
            "created_at": note.created_at.isoformat()
        }
        for note in orphaned
    ]
    return JSONResponse(content=data)
```

**Alternative considered:** No bulk operations
- Rejected: Tedious for users with many orphaned entries

### Decision 7: Confidence Score Displayed to User

**Rationale:** Transparency. User should know how confident the system is about suggested match.

**UI:**
```jsx
{suggestedMatch && (
  <Alert severity={confidence >= 80 ? "info" : "warning"}>
    <Badge 
      color={confidence >= 80 ? "green" : "yellow"}
    >
      {confidence}% confident
    </Badge>
    Suggested: AAPL 2024-03-15 10:30-11:45
    <Button>Link to This Trade</Button>
  </Alert>
)}
```

**Alternative considered:** Hide confidence score
- Rejected: User can't judge if they should trust the suggestion

## Risks / Trade-offs

### Risk 1: Auto-matching links to wrong trade

**Impact:** User's note attached to wrong trade, loses context.

**Mitigation:**
- Only auto-link confidence >= 100% (±1 hour, exact symbol)
- Lower confidence → suggest only, require user confirmation
- User can manually unlink and re-link (future enhancement)

### Risk 2: Multiple orphaned notes match same trade

**Impact:** All notes linked to same trade (data loss if wrong match).

**Mitigation:**
- Algorithm picks highest confidence match
- User can review and manually unlink in trade detail view
- Future: Detect conflicts and flag for manual review

### Risk 3: User deletes orphaned entries then regrets

**Impact:** Valuable notes permanently lost.

**Mitigation:**
- Export button: Download JSON backup before deleting
- Confirmation dialog: "This cannot be undone"
- Documentation: Recommend export before bulk delete

### Risk 4: Backfill migration fails on large datasets

**Impact:** Migration times out, deployment blocked.

**Mitigation:**
- Test migration on staging with production data clone
- Break into batches if needed (UPDATE ... LIMIT 1000)
- Run migration during low-traffic window

## Implementation Details

### Auto-Matching Service

```python
class JournalingService:
    async def auto_match_orphaned(self, db: AsyncSession) -> int:
        """Run auto-matching after import. Returns count of matched entries."""
        orphaned_notes = await self._get_orphaned_notes(db)
        orphaned_tags = await self._get_orphaned_tags(db)
        orphaned_playbooks = await self._get_orphaned_playbooks(db)
        
        trades = await self._get_all_trades(db)
        
        matched_count = 0
        
        for note in orphaned_notes:
            match = self._find_match(note, trades)
            if match and match.confidence >= 100:
                note.trade_id = match.trade_id
                matched_count += 1
        
        # Repeat for tags, playbooks
        
        await db.commit()
        return matched_count
    
    def _find_match(self, entry, trades) -> Optional[Match]:
        # Heuristic algorithm (see Decision 2)
        pass
```

### Orphaned Journaling API

```python
class OrphanedEntryResponse(BaseModel):
    id: int
    type: Literal["note", "tag", "playbook"]
    content: str
    symbol: str
    opened_at: datetime
    closed_at: Optional[datetime]
    
    suggested_match: Optional[SuggestedMatch]

class SuggestedMatch(BaseModel):
    trade_id: int
    trade_symbol: str
    trade_opened_at: datetime
    confidence: int  # 0-100

@router.get("/journaling/orphaned")
async def get_orphaned_entries(db: AsyncSession):
    # Get all orphaned notes, tags, playbooks
    # Run matching heuristic
    # Return with suggested matches
    pass

@router.post("/journaling/{id}/link")
async def link_to_trade(
    id: int,
    trade_id: int = Body(...),
    db: AsyncSession = Depends(get_db)
):
    # Update trade_id for note/tag/playbook
    pass
```

## Migration Plan

### Phase 1: Database Schema

**Migration:** Add symbol, opened_at, closed_at to journaling tables
```sql
ALTER TABLE trade_notes ADD COLUMN symbol VARCHAR(20);
ALTER TABLE trade_notes ADD COLUMN opened_at TIMESTAMP;
ALTER TABLE trade_notes ADD COLUMN closed_at TIMESTAMP;

-- Backfill existing rows
UPDATE trade_notes 
SET symbol = trades.symbol,
    opened_at = trades.opened_at,
    closed_at = trades.closed_at
FROM trades
WHERE trade_notes.trade_id = trades.id;

-- Repeat for trade_tags, trade_playbooks
```

### Phase 2: Backend Service & API

- Implement JournalingService.auto_match_orphaned()
- Add API endpoints for orphaned management
- Update create_note() / add_tag() / link_playbook() to populate metadata

### Phase 3: Frontend UI

- Create OrphanedJournaling page
- Add navigation link (conditional, if orphaned count > 0)
- Implement manual link dialog
- Implement bulk operations

### Phase 4: Integration with Fresh Start

- Call auto_match_orphaned() after Fresh Start import completes
- Include matched count in import summary

## Edge Cases

### Edge Case 1: No orphaned entries

**Scenario:** User has never deleted trades or run Fresh Start.

**Result:** Orphaned Journaling link hidden in navigation (orphanedCount = 0).

### Edge Case 2: Orphaned entry with no metadata

**Scenario:** Entry created before Change 3 (no symbol, opened_at fields).

**Result:** Can't auto-match, shown in orphaned list as "Unknown trade". User can manually link or delete.

### Edge Case 3: Multiple trades match (same symbol, same day)

**Scenario:** AAPL traded twice on 2024-03-15 (morning + afternoon).

**Result:** Algorithm picks closest time match. If equally close, picks first. User can manually re-link if wrong.

### Edge Case 4: Orphaned entry from deleted manual trade

**Scenario:** User created manual trade (no broker data), journaled it, then deleted trade.

**Result:** Auto-matching can still work if symbol + dates populated. If not, manual link required.

## Open Questions

None - all design decisions resolved.
