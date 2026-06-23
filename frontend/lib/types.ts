/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * TypeScript interfaces mirroring the backend Pydantic schemas.
 */

// ─── Enums ────────────────────────────────────────────────────────────────────

export type Direction = "LONG" | "SHORT";

export type AssetClass =
  | "EQUITY"
  | "OPTION"
  | "FUTURE"
  | "FOREX"
  | "CRYPTO";

// ─── Common ───────────────────────────────────────────────────────────────────

export interface ResponseEnvelope<T> {
  data: T;
  meta: Record<string, unknown>;
}

export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
  total: number | null;
}

export interface OffsetPage<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface OIDCConfig {
  enabled: boolean;
  provider_name: string;
}

export interface AuthConfigResponse {
  google_enabled: boolean;
  oidc: OIDCConfig;
  local_auth_enabled: boolean;
  password_reset_enabled: boolean;
}

// ─── User ─────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
}

// ─── Account ──────────────────────────────────────────────────────────────────

export type AccountType = "manual" | "schwab" | "ibkr";

export type FlexFromDatePreset = "ytd" | "custom";

export interface AccountSettings {
  sync_days: number;
  flex_from_date_preset: FlexFromDatePreset;
  flex_custom_from_date: string | null;
}

export interface Account {
  id: string;
  user_id: string;
  portfolio_id: string | null;
  name: string;
  account_number: string | null;
  type: AccountType;
  currency: string;
  is_active: boolean;
  has_api_keys: boolean;
  settings: AccountSettings;
  created_at: string;
}

export interface AccountCreate {
  name: string;
  portfolio_id?: string | null;
  account_number?: string | null;
  type?: AccountType;
  currency?: string;
  properties?: Record<string, string> | null;
  settings?: Partial<AccountSettings> | null;
}

// ─── Playbook ─────────────────────────────────────────────────────────────────

export interface Playbook {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  content_markdown: string | null;
  target_winrate: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  taxonomies?: TaxonomyResponse[];
}

export interface PlaybookCreate {
  name: string;
  description?: string;
  content_markdown?: string | null;
  target_winrate?: number | string | null;
}

export interface PlaybookUpdate {
  name?: string;
  description?: string | null;
  content_markdown?: string | null;
  target_winrate?: number | string | null;
  is_active?: boolean;
}

// ─── Tag ──────────────────────────────────────────────────────────────────────

export interface Tag {
  id: string;
  user_id: string;
  name: string;
  color: string | null;
  created_at: string;
}

export interface TagCreate {
  name: string;
  color?: string;
}

// ─── TradeNote ────────────────────────────────────────────────────────────────

export interface TradeNote {
  id: string;
  trade_id: string;
  user_id: string;
  content: string;
  emotion: string | null;
  created_at: string;
  updated_at: string;
}

export interface TradeNoteCreate {
  content: string;
  emotion?: string;
}

export interface TradeNoteUpdate {
  content?: string;
  emotion?: string | null;
}

// ─── Trade ────────────────────────────────────────────────────────────────────

export interface Trade {
  id: string;
  position_id: string | null;
  symbol: string;
  direction: Direction;
  asset_class: AssetClass | null;
  is_combo: boolean;
  multiplier: number;
  quantity: string | null;
  entry_price: string | null;
  exit_price: string | null;
  stop_loss: string | null;
  take_profit: string | null;
  opened_at: string;
  closed_at: string | null;
  pnl: string | null;
  net_pnl: string | null;
  commission: string;
  notes: string | null;
  user_rating: number | null;
  currency: string | null;
  pnl_eur: string | null;
  net_pnl_eur: string | null;
  tradingview_link: string | null;
  image_urls: string[];
  playbook_id: string | null;
  playbook_name: string | null;
  account_id: string | null;
  account_name: string | null;
  account_type: string | null;
  taxonomies?: TaxonomyResponse[];
  annotations?: TradeAnnotationResponse[];
  created_at: string;
  updated_at: string;
  is_manually_edited: boolean;
  tags: Array<{ id: string; name: string; color: string | null }>;
  trade_notes: TradeNote[];
  legs?: LogicalExecution[];
}

export interface TradeCreate {
  symbol: string;
  direction: Direction;
  asset_class?: AssetClass | null;
  is_combo?: boolean;
  quantity?: string | null;
  entry_price?: string | null;
  exit_price?: string | null;
  stop_loss?: string | null;
  take_profit?: string | null;
  opened_at: string;
  closed_at?: string | null;
  pnl?: string | null;
  commission?: string;
  currency?: string | null;
  notes?: string | null;
  image_urls?: string[];
  account_id?: string | null;
  playbook_id?: string | null;
  taxonomy_ids?: string[];
  executions?: LogicalExecutionCreate[] | null;
}

export interface TradeUpdate {
  symbol?: string | null;
  direction?: Direction | null;
  asset_class?: AssetClass | null;
  stop_loss?: string | null;
  take_profit?: string | null;
  pnl?: string | null;
  commission?: string | null;
  notes?: string | null;
  user_rating?: number | null;
  tradingview_link?: string | null;
  image_urls?: string[] | null;
  playbook_id?: string | null;
  taxonomy_ids?: string[] | null;
  is_manually_edited?: boolean | null;
}

// ─── Centralized metadata ─────────────────────────────────────────────────────

export type MetadataScope = "trades" | "checkins" | "both" | "playbook";

export type AnnotationType = "int" | "float" | "bool" | "string_enum";

export interface TaxonomyResponse {
  id: string;
  name: string;
  scope: MetadataScope;
  color_hex: string;
  description?: string | null;
  icon_identifier?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaxonomyCreate {
  name: string;
  scope: MetadataScope;
  color_hex: string;
  description?: string | null;
  icon_identifier?: string | null;
}

export interface TaxonomyUpdate {
  name?: string;
  scope?: MetadataScope;
  color_hex?: string;
  description?: string | null;
  icon_identifier?: string | null;
}

export interface AnnotationDefinitionResponse {
  id: string;
  name: string;
  type: AnnotationType;
  scope: MetadataScope;
  description?: string | null;
  scale_labels?: Record<string, unknown> | null;
  icon_identifier?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface AnnotationDefinitionCreate {
  name: string;
  type: AnnotationType;
  scope: MetadataScope;
  description?: string | null;
  scale_labels?: Record<string, unknown> | null;
  icon_identifier?: string | null;
}

export interface AnnotationDefinitionUpdate {
  name?: string;
  type?: AnnotationType;
  scope?: MetadataScope;
  description?: string | null;
  scale_labels?: Record<string, unknown> | null;
  icon_identifier?: string | null;
}

export interface TradeAnnotationResponse {
  trade_id: string;
  annotation_definition_id: string;
  definition: AnnotationDefinitionResponse;
  value: string | number | boolean;
}

export interface CheckinAnnotationResponse {
  checkin_id: string;
  annotation_definition_id: string;
  definition: AnnotationDefinitionResponse;
  value: string | number | boolean;
}

// ─── Metrics ──────────────────────────────────────────────────────────────────

export interface TradeMetrics {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  breakeven_trades: number;
  win_rate: string;
  loss_rate: string;
  avg_win: string;
  avg_loss: string;
  profit_factor: string | null;
  expectancy: string;
  total_pnl: string;
  gross_profit: string;
  gross_loss: string;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  avg_trade_duration_seconds: number | null;
  sharpe_ratio: string | null;
}

export interface EquityCurvePoint {
  timestamp: string;
  equity: string;
  pnl: string;
}

export interface DrawdownPoint {
  timestamp: string;
  drawdown: string;
  drawdown_abs: string;
}

export interface MetricsSummary {
  metrics: TradeMetrics;
  max_drawdown: string;
  max_drawdown_abs: string;
  equity_curve: EquityCurvePoint[];
  drawdown_curve: DrawdownPoint[];
}

// ─── Import ───────────────────────────────────────────────────────────────────

export interface ImportResult {
  broker: string;
  filename: string;
  trades_parsed: number;
  trades_created: number;
  trades_skipped: number;
  raw_suppressed_skipped?: number;
  raw_deleted_skipped?: number;
  warnings: string[];
}

/** Result returned by POST /imports/{account_id}/fresh-start (task 8.6). */
export interface FreshStartResult {
  account_id: string;
  executions_deleted: number;
  trades_deleted: number;
  import_result: ImportResult;
}

// ─── Daily / Monthly PnL ─────────────────────────────────────────────────────

export interface DailyPnl {
  date: string;
  pnl: string;
  trade_count: number;
}

export interface MonthlyPnl {
  year: number;
  month: number;
  pnl: string;
  trade_count: number;
  win_rate: string;
}

export interface PnlBySymbol {
  symbol: string;
  total_pnl: string;
  trade_count: number;
  win_rate: string;
  avg_pnl: string;
}

export interface PnlByAssetClass {
  asset_class: AssetClass;
  total_pnl: string;
  trade_count: number;
  win_rate: string;
}

export interface ReturnDistribution {
  bucket_min: string;
  bucket_max: string;
  count: number;
  frequency: string;
}

// ─── Account (extended) ───────────────────────────────────────────────────────

export interface AccountUpdate {
  name?: string;
  portfolio_id?: string | null;
  account_number?: string | null;
  type?: AccountType;
  currency?: string;
  is_active?: boolean;
  properties?: Record<string, string> | null;
  settings?: Partial<AccountSettings> | null;
}

// ─── Rolling Winrate ──────────────────────────────────────────────────────────

export interface RollingWinratePoint {
  trade_index: number;
  closed_at: string;
  rolling_winrate: number;
  window: number;
}

// ─── Broker / Schwab / IBKR ───────────────────────────────────────────────────

export interface BrokerStatusResponse {
  connected: boolean;
  last_sync_at: string | null;
}

export interface BrokerSyncResult {
  imported_count: number;
  skipped_count: number;
  errors: string[];
}

// ─── User Settings ────────────────────────────────────────────────────────────

export type Theme = "system" | "light" | "dark";
export type DefaultDateRange = "all" | "ytd" | "last30";

export interface UserSettings {
  theme: Theme;
  default_date_range: "all" | "ytd" | "last30";
  show_open_trades?: boolean;
  features?: Record<string, boolean>;
  chart_candles_before?: number;
  chart_candles_after?: number;
  chart_show_post_exit?: boolean;
  default_portfolio_id?: string | null;
  home_route?: "/dashboard" | "/dashboard/trades" | "/dashboard/library" | "/dashboard/checkins";
  chart_intervals?: Array<"1h" | "4h" | "1d" | "1w">;
}

export interface UserSettingsUpdate {
  theme?: Theme;
  default_date_range?: "all" | "ytd" | "last30";
  show_open_trades?: boolean;
  features?: Record<string, boolean>;
  chart_candles_before?: number;
  chart_candles_after?: number;
  chart_show_post_exit?: boolean;
  default_portfolio_id?: string;
  home_route?: "/dashboard" | "/dashboard/trades" | "/dashboard/library" | "/dashboard/checkins";
  chart_intervals?: Array<"1h" | "4h" | "1d" | "1w"> | null;
}

// ─── Corporate Actions ────────────────────────────────────────────────────────

export interface CorporateAction {
  id: string;
  user_id: string;
  symbol: string;
  /** ISO 8601 date string (e.g. "2023-05-01") */
  date: string;
  /** Split ratio: after / before (e.g. "0.05" for 1:20 reverse split) */
  ratio: string;
  old_conid: string | null;
  new_conid: string | null;
  created_at: string;
  updated_at: string;
}

export interface CorporateActionCreate {
  symbol: string;
  date: string;
  ratio: string;
  old_conid?: string | null;
  new_conid?: string | null;
}

export interface CorporateActionUpdate {
  symbol?: string;
  date?: string;
  ratio?: string;
  old_conid?: string | null;
  new_conid?: string | null;
}

// ─── Bulk Operations ─────────────────────────────────────────────────────────

export interface BulkDeletePayload {
  trade_ids: string[];
}

export interface BulkAssignTagPayload {
  trade_ids: string[];
  tag_ids: string[];
  mode: "add" | "remove";
}

export interface BulkAssignPlaybookPayload {
  trade_ids: string[];
  playbook_id: string | null;
}

// ─── Saved Trade Filters ─────────────────────────────────────────────────────

export type FilterScope = "SYSTEM" | "USER";

export interface SavedTradeFilterBase {
  name: string;
  definition: Record<string, any>;
}

export interface SavedTradeFilterCreate extends SavedTradeFilterBase {}

export interface SavedTradeFilterUpdate {
  name?: string;
  definition?: Record<string, any>;
}

export interface SavedTradeFilterRead extends SavedTradeFilterBase {
  id: string;
  scope: FilterScope;
  owner_id: string | null;
  needs_review: boolean;
  created_at: string;
  updated_at: string;
}

export interface TradePartialCloseRequest {
  quantity: number;
  exit_price: number;
  closed_at: string;
  exit_commission?: number | null;
}

// ─── Executions ──────────────────────────────────────────────────────────────

/** Origin type for a logical execution (task 8.1). */
export type ExecutionOrigin = 'imported' | 'manual' | 'merged' | 'split';

/**
 * @deprecated Use ExecutionOrigin instead. Kept for backward compatibility.
 */
export type ExecutionStatus = ExecutionOrigin;

export interface LogicalExecution {
  id: string;
  trade_id: string | null;
  user_id: string;
  account_id: string | null;
  symbol: string;
  asset_class: AssetClass;
  conid: string | null;
  direction: Direction;
  quantity: string;
  price: string;
  commission: string;
  pnl: string | null;
  pnl_eur: string | null;
  executed_at: string;
  /** @deprecated Use `origin` instead. */
  status?: ExecutionOrigin;
  /** Origin of this execution: how it was created (task 8.2). */
  origin: ExecutionOrigin;
  /** When true, this execution has been soft-deleted (task 8.2). */
  deleted: boolean;
  /** When true, this imported execution has been manually edited (task 8.2). */
  user_modified: boolean;
  /** ID of the parent execution when origin is 'split' or 'merged' (lineage). */
  parent_id: string | null;
  currency: string | null;
  multiplier: number;
  created_at: string;
  updated_at: string;
}

export interface LogicalExecutionCreate {
  direction: Direction;
  quantity: string;
  price: string;
  commission?: string;
  executed_at: string;
  pnl?: string | null;
  asset_class?: AssetClass | null;
  multiplier?: number;
}

export interface LogicalExecutionUpdate {
  direction?: Direction;
  quantity?: string;
  price?: string;
  commission?: string;
  executed_at?: string;
  pnl?: string | null;
}

export interface ReassignExecutionRequest {
  target_trade_id: string;
}

// ─── Split Execution (task 8.9) ───────────────────────────────────────────────

export interface SplitExecutionRequest {
  quantity_a: string;
  quantity_b: string;
  price_a?: string | null;
  price_b?: string | null;
  executed_at_a?: string | null;
  executed_at_b?: string | null;
}

export interface SplitExecutionResponse {
  execution_a: LogicalExecution;
  execution_b: LogicalExecution;
  original: LogicalExecution;
}

// ─── Merge ────────────────────────────────────────────────────────────────────

export interface MergeTradesRequest {
  trade_ids: string[];
}
