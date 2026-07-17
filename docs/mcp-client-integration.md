## MCP Client Integration Guide

## Available Tools

### `get_metadata_schema`

Returns the active metadata vocabulary (taxonomies and annotation definitions) for the authenticated user.

| Param | Type | Required | Description |
|---|---|---|---|
| _(none)_ | object | no | No input fields are required. |

### `search_trades_advanced`

Finds trades using multi-dimensional filters across time, instrument, performance, taxonomy tags, annotation values, and portfolio scope.

| Param | Type | Required | Description |
|---|---|---|---|
| `date_from` | string (date-time) | no | Lower bound for `opened_at` (inclusive). |
| `date_to` | string (date-time) | no | Upper bound for `opened_at` (inclusive). |
| `symbol` | string | no | Case-insensitive symbol match (`ILIKE`). |
| `asset_class` | enum | no | One of `EQUITY`, `OPTION`, `FUTURE`, `FOREX`, `CRYPTO`. |
| `pnl_min` | number | no | Minimum realized P&L. |
| `pnl_max` | number | no | Maximum realized P&L. |
| `taxonomy_ids` | uuid[] | no | Must match all provided taxonomy IDs (AND semantics). |
| `annotation_filters` | object[] | no | Array of filters: `{ annotation_definition_id, operator, value }`. |
| `portfolio_id` | uuid | no | Restrict trades to accounts in one portfolio. |
| `limit` | integer | no | Page size (default `50`, max `200`). |
| `offset` | integer | no | Pagination offset (default `0`). |

### `sync_trade_metadata`

Performs bulk metadata sync for many trades in one call (notes, taxonomy assignments, annotation values).

| Param | Type | Required | Description |
|---|---|---|---|
| `trade_ids` | uuid[] | yes | Target trade IDs (owned IDs are applied, foreign/nonexistent IDs skipped). |
| `notes` | string | no | Replaces `Trade.notes` on matched trades. |
| `taxonomy_ids` | uuid[] | no | Replaces all taxonomy assignments per matched trade. |
| `annotations` | object[] | no | Upserts annotations: `{ annotation_definition_id, value }`. |

### `sync_playbook_metadata`

Performs additive, idempotent taxonomy assignment for a single playbook.

| Param | Type | Required | Description |
|---|---|---|---|
| `playbook_id` | uuid | yes | Target playbook ID (must be owned by the caller). |
| `taxonomy_ids` | uuid[] | yes | Taxonomy IDs to add. Existing assignments are preserved; duplicates are ignored. |

### `create_strategy_playbook`

Creates a new active playbook with optional markdown description.

| Param | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Playbook name, max 100 chars, unique per user. |
| `description` | string | no | Optional markdown description. |
| `target_winrate` | number | no | Optional target win rate, `0.0` to `1.0`. |

### `update_strategy_playbook`

Updates playbook metadata and can optionally assign taxonomy tags in the same call.

| Param | Type | Required | Description |
|---|---|---|---|
| `playbook_id` | uuid | yes | Target playbook ID. |
| `name` | string | no | Optional renamed playbook name (unique per user). |
| `description` | string | no | Optional markdown description update. |
| `taxonomy_ids` | uuid[] | no | Optional additive taxonomy assignment list (same semantics as `sync_playbook_metadata`). |
| `target_winrate` | number | no | Optional target win rate, `0.0` to `1.0`. |
| `is_active` | boolean | no | Optional active status update. |

## Prompt Examples

Here are some example prompts you can use directly with your connected AI client:

**Performance discovery:**
```text
Show me all losing trades from last week where my Mood annotation was below 5.
```
*(Uses: `search_trades_advanced`)*

**Automated enrichment:**
```text
Tag my trades from May 6th 2026 afternoon with 'Macro Volatility'.
```
*(Uses: `get_metadata_schema` + `search_trades_advanced` + `sync_trade_metadata`)*

**Strategy creation:**
```text
Create a Breakout Momentum playbook from these rules: enter after first pullback, risk 1R, move stop to break-even after 1R.
```
*(Uses: `create_strategy_playbook`)*

**Pattern correlation:**
```text
What is my win rate on LONG EQUITY trades in the first hour of the day?
```
*(Uses: `search_trades_advanced`)*

**Deep Dive:**
```text
Retrieve all trades tagged with 'Earnings Gap Fill' from last month, identify common mistakes among the losing trades, and suggest 3 rules to improve adherence.
```
*(Uses: `search_trades_advanced` + `get_metadata_schema`)*

**Risk Assessment:**
```text
Analyze my Max Drawdown periods over the last 90 days. Were there any correlation with specific Market Phases or specific assets?
```
*(Uses: `search_trades_advanced`)*

## Workflow Example

1) Learn the user's metadata vocabulary with `get_metadata_schema`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_metadata_schema",
    "arguments": {}
  }
}
```

2) Find candidate trades with `search_trades_advanced`:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "search_trades_advanced",
    "arguments": {
      "date_from": "2026-05-06T13:00:00Z",
      "date_to": "2026-05-06T20:00:00Z",
      "symbol": "NVDA",
      "limit": 50,
      "offset": 0
    }
  }
}
```

3) Enrich those trades in bulk with `sync_trade_metadata`:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "sync_trade_metadata",
    "arguments": {
      "trade_ids": [
        "5e4ab6b2-e0be-4a08-8878-8a449026f8e2",
        "73bd8cc4-54c1-4b72-b5f8-d6f3f7e3f8b3"
      ],
      "taxonomy_ids": ["f2a60a74-8505-4f2b-9279-755ca7f1f6de"],
      "notes": "MCP bulk enrichment for macro volatility review"
    }
  }
}
```

## Constraints & Limits

- `sync_trade_metadata` accepts a maximum of 50 `trade_ids` per call.
- `search_trades_advanced` page size maximum is 200 results.
- `annotation_filters` require either a `symbol` filter or a full `date_from` + `date_to` range.

### Claude Desktop Configuration (using SSE Proxy)

Create or edit `claude_desktop_config.json` to include the following `sse_proxy` block. This tells Claude Desktop to launch the official `@modelcontextprotocol/sse-proxy` which translates stdio to the MCP SSE endpoint and injects the PAT.

```json
{
  "sse_proxy": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/sse-proxy",
      "http://localhost:8000/mcp/sse"
    ],
    "env": {
      "AUTHORIZATION": "Bearer <YOUR_PAT>"
    }
  }
}
```

Replace `<YOUR_PAT>` with the token generated in the previous section.

### OpenCode Configuration Example

For OpenCode, set the `AUTHORIZATION` environment variable before invoking the client:

```bash
export AUTHORIZATION="Bearer <YOUR_PAT>"
opencode --mcp http://localhost:8000/mcp/sse
```

### Claude Configuration Example
```bash
claude mcp add tradesensei \
  npx mcp-remote http://localhost:8000/mcp/sse \
  --header "Authorization: Bearer  <YOUR_PAT>"
```


## Generating a Personal Access Token (PAT)

1. Log in to the Trade Sensei web UI.
2. Navigate to **Settings → API Tokens**.
3. Click **Create New Token**.
4. Give the token a descriptive name (e.g., `MCP Integration`) and set the **Scope** to *MCP*.
5. Click **Generate**. The token will be displayed **once** – copy it safely.
6. Store the token in a secure location (e.g., password manager) and treat it like a password.

### Using the PAT with the MCP Server

The MCP server expects the token in the `Authorization` header as a Bearer token:

```
Authorization: Bearer <YOUR_PAT>
```

All MCP endpoints (`/mcp/*`) will reject requests without a valid PAT with `401 Unauthorized`.

### Token Rotation

- Tokens can be revoked from the **API Tokens** page.
- After revocation, generate a new token and update your client configuration.
- Rotate tokens regularly (e.g., every 90 days) to reduce risk.
