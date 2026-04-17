## Why

The current model ties each trade to a single `symbol`/`asset_class` pair and uses VWAP re-aggregation across all its legs. This breaks down for multi-instrument positions on the same underlying: a covered call (AAPL equity + short AAPL call), a protective put (AAPL equity + long AAPL put), or a collar — these are one logical position whose legs span two different instruments. There is no way today to model them as a single entity, nor to see their combined P&L without manual math.

## What Changes

- **New `is_combo` flag on `Trade`** (boolean, default `false`): marks a trade as a multi-instrument COMBO position.
- **Alembic migration**: adds `is_combo` column to `trades`.
- **Modified re-aggregation for COMBO trades**: when `is_combo=true`, `_re_aggregate_trade()` skips VWAP-based `entry_price`, `exit_price`, and `quantity` (meaningless across different instruments); still sums `pnl` and `commission`, still sets `MIN(opened_at)` and `MAX(closed_at)`.
- **`TradeCreate` and `TradeUpdate`** gain `is_combo: bool = False`.
- **`TradeRead`** gains `is_combo: bool`.
- **ExecutionLegsTable**: for COMBO trades, adds a `Symbol` and `Asset Class` column per row so the user can see which leg belongs to which instrument.
- **Trade detail badge**: COMBO badge replaces the directional LONG/SHORT badge when `is_combo=true`.
- **Trade list**: COMBO indicator in the asset-class/direction column.
- **Manual COMBO trade creation**: `TradeForm` gets a "COMBO" toggle in create mode; enabling it clears the single `asset_class` field (irrelevant) and lets the user add legs with mixed symbols/asset classes.

## Capabilities

### New Capabilities
- `combo-positions`: Create and manage COMBO (multi-instrument) positions; add execution legs from different instruments on the same underlying; view combined P&L and commission across all legs while individual leg P&L remains per-instrument.

### Modified Capabilities

## Impact

- **Backend**: `Trade` model (`is_combo`); `_re_aggregate_trade()` in `execution.py` (branch for COMBO); `TradeCreate`, `TradeUpdate`, `TradeRead` schemas.
- **Frontend**: `ExecutionLegsTable` (Symbol + Asset Class columns for COMBO), trade detail page (COMBO badge), trades list (COMBO indicator), `TradeForm` create mode (COMBO toggle).
- **No breaking changes**: `is_combo` defaults to `false`; all existing trades and API consumers are unaffected.
- **No changes** to FIFO logic, re-aggregation trigger chain, or RLS.
