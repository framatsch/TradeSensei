## ADDED Requirements

### Requirement: Protection applies to every ingestion entry point

The execution-overwrite protections — protected-trade rebuild isolation, orphan-lot suppression for protected contracts, backfill link guarding, and protection reporting — SHALL hold for every path by which broker data enters the system, including file upload, scheduled account sync, and direct broker API pull. No ingestion path may reach trade persistence without passing through the protected-trade isolation.

This requirement exists because the protections were implemented in `ImportService` while the IBKR Flex sync used a separate implementation. A protected trade was correctly preserved while the sync simultaneously created phantom sentinel trades shadowing the same contracts, so the account was corrupted despite the protection working exactly as specified.

#### Scenario: Protected trade survives an API sync

- **GIVEN** a metadata-protected trade `T`
- **WHEN** trade data covering `T`'s contracts arrives through a broker API sync rather than a file upload
- **THEN** `T`'s structural fields SHALL be unchanged
- **THEN** `T`'s executions SHALL remain linked to `T`
- **THEN** no sentinel orphan trade SHALL be created for a contract held by `T`

#### Scenario: Protection uses execution identity on every path

- **WHEN** any ingestion path determines whether a trade is protected
- **THEN** it SHALL use the protected-execution snapshot
- **THEN** it SHALL NOT use the `(broker_conid, opened_at)` match key, which does not survive FIFO re-slicing

#### Scenario: Protection outcomes are reported on every path

- **WHEN** a protection-driven skip or unlinked execution occurs during any ingestion
- **THEN** the outcome SHALL appear in the result returned to the caller and in the application log
