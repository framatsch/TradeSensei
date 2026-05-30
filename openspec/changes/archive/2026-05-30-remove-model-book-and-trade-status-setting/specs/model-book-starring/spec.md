## REMOVED Requirements

### Requirement: Trades can be starred into the Model Book
**Reason**: The Model Book feature is superseded by the Taxonomy system. The star/bookmark mechanism on trades is removed entirely.
**Migration**: Users who relied on Model Book starring to mark important trades should use the Taxonomy tagging system instead. Existing starred data is not migrated.

### Requirement: Check-ins can be starred into the Model Book
**Reason**: The Model Book feature is superseded by the Taxonomy system. The star/bookmark mechanism on check-ins is removed entirely.
**Migration**: Users who relied on starring check-ins should use Taxonomy tags or check-in notes instead. Existing starred data is not migrated.

### Requirement: Model Book gallery endpoint returns starred entries
**Reason**: No gallery without the starring mechanism.
**Migration**: No replacement endpoint. Taxonomy browsing will provide equivalent classification-based views in a future change.

### Requirement: is_modelbook field returned in trade and check-in API responses
**Reason**: Field removed from DB schema; no longer meaningful.
**Migration**: Clients that read `is_modelbook` from trade or check-in responses must remove those references. The field will no longer be present in API responses.
