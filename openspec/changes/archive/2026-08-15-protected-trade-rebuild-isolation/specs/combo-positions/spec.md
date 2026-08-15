## ADDED Requirements

### Requirement: Manual trade merge derives combo classification

When the user merges trades, the system SHALL set `is_combo=true` on the surviving trade when its resulting set of non-deleted executions spans two or more distinct `conid` values, and SHALL do so before re-aggregating the survivor so the combo aggregation branch is used. The merge validation SHALL permit differing `asset_class` across the merged trades when the result qualifies as a combo, and SHALL continue to require a matching `symbol` and `account_id`.

This closes the gap where a multi-leg position the importer did not recognise as a combo (for example legs opened in separate broker orders) could only be repaired by a manual merge, which previously produced a non-combo trade whose re-aggregation computed a volume-weighted average entry and exit price across different contracts — a meaningless value for a spread.

#### Scenario: Merging two option legs produces a combo trade

- **GIVEN** two closed option trades on the same symbol and account with different `conid` values
- **WHEN** the user merges them
- **THEN** the surviving trade SHALL have `is_combo=true`
- **THEN** the survivor SHALL be aggregated using the combo branch, leaving `entry_price`, `exit_price`, and `quantity` unset
- **THEN** the survivor's `pnl` SHALL be the sum of its closing legs' broker-reported PnL and `net_pnl` SHALL be that value less total commission

#### Scenario: Merging trades on a single contract stays non-combo

- **GIVEN** two trades whose combined executions all share one `conid`
- **WHEN** the user merges them
- **THEN** the surviving trade SHALL retain `is_combo=false`
- **THEN** the survivor SHALL be aggregated using the standard entry/exit branch

#### Scenario: Differing asset class is permitted when the result is a combo

- **GIVEN** two trades on the same symbol and account with different `asset_class` values and different `conid` values
- **WHEN** the user merges them
- **THEN** the merge SHALL succeed and produce a combo trade

#### Scenario: Mismatched symbol or account is still rejected

- **GIVEN** two trades with different `symbol` or different `account_id`
- **WHEN** the user attempts to merge them
- **THEN** the merge SHALL be rejected
