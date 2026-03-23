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
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PlaybookCreate {
  name: string;
  description?: string;
}

export interface PlaybookUpdate {
  name?: string;
  description?: string | null;
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
  symbol: string;
  direction: Direction;
  asset_class: AssetClass;
  quantity: string;
  entry_price: string;
  exit_price: string | null;
  stop_loss: string | null;
  take_profit: string | null;
  opened_at: string;
  closed_at: string | null;
  pnl: string | null;
  commission: string;
  currency: string | null;
  pnl_eur: string | null;
  notes: string | null;
  account_id: string | null;
  account_name: string | null;
  account_type: AccountType | null;
  playbook_id: string | null;
  playbook_name: string | null;
  tags: Tag[];
  trade_notes: TradeNote[];
  created_at: string;
  updated_at: string;
  tradingview_link?: string | null;
  screenshots?: string[];
  is_manually_edited: boolean;
}

export interface TradeCreate {
  symbol: string;
  direction: Direction;
  asset_class: AssetClass;
  quantity: string;
  entry_price: string;
  exit_price?: string | null;
  stop_loss?: string | null;
  take_profit?: string | null;
  opened_at: string;
  closed_at?: string | null;
  pnl?: string | null;
  commission?: string;
  currency?: string | null;
  notes?: string | null;
  account_id?: string | null;
  playbook_id?: string | null;
  tag_ids?: string[];
}

export interface TradeUpdate {
  symbol?: string | null;
  direction?: Direction | null;
  asset_class?: AssetClass | null;
  quantity?: string | null;
  entry_price?: string | null;
  exit_price?: string | null;
  stop_loss?: string | null;
  take_profit?: string | null;
  opened_at?: string | null;
  closed_at?: string | null;
  pnl?: string | null;
  commission?: string | null;
  notes?: string | null;
  tradingview_link?: string | null;
  playbook_id?: string | null;
  tag_ids?: string[] | null;
  currency?: string | null;
  is_manually_edited?: boolean | null;
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
  cash_transactions_parsed: number;
  cash_transactions_created: number;
  cash_transactions_skipped: number;
  warnings: string[];
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
  account_number?: string | null;
  type?: AccountType;
  currency?: string;
  is_active?: boolean;
  properties?: Record<string, string> | null;
  settings?: Partial<AccountSettings> | null;
}

// ─── Tax ──────────────────────────────────────────────────────────────────────

export interface TaxCategoryBlock {
  gains_eur: string;
  losses_eur: string;
  net_eur: string;
  trade_count: number;
}

export interface AccountTaxSummary {
  account_id: string | null;
  account_name: string | null;
  equities: TaxCategoryBlock;
  derivatives: TaxCategoryBlock;
  total_net_eur: string;
  trades_missing_eur: number;
  dividends_eur: string;
  withholding_tax_eur: string;
  interest_eur: string;
}

export interface TaxAnnualSummary {
  year: number;
  equities: TaxCategoryBlock;
  derivatives: TaxCategoryBlock;
  total_net_eur: string;
  trades_missing_eur: number;
  dividends_eur: string;
  withholding_tax_eur: string;
  interest_eur: string;
  accounts: AccountTaxSummary[];
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
  default_date_range: DefaultDateRange;
}

export interface UserSettingsUpdate {
  theme?: Theme;
  default_date_range?: DefaultDateRange;
}

// ─── Cash Transactions ────────────────────────────────────────────────────────

export type CashTransactionType =
  | "DIVIDEND"
  | "WITHHOLDING_TAX"
  | "DEPOSIT"
  | "WITHDRAWAL"
  | "INTEREST"
  | "FEE"
  | "OTHER";

export interface CashTransaction {
  id: string;
  account_id: string;
  date: string;
  type: CashTransactionType;
  symbol: string | null;
  amount: string;
  currency: string;
  amount_eur: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface CashTransactionCreate {
  date: string;
  type: CashTransactionType;
  symbol?: string | null;
  amount: string;
  currency: string;
  amount_eur?: string | null;
  description?: string | null;
}

export interface CashTransactionUpdate {
  date?: string;
  type?: CashTransactionType;
  symbol?: string | null;
  amount?: string;
  currency?: string;
  amount_eur?: string | null;
  description?: string | null;
}

export interface AccountMetrics {
  total_dividends: string;
  total_withholding_tax: string;
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
