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

export interface Account {
  id: string;
  user_id: string;
  name: string;
  broker: string | null;
  currency: string;
  is_active: boolean;
  created_at: string;
}

export interface AccountCreate {
  name: string;
  broker?: string | null;
  currency?: string;
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
  notes: string | null;
  playbook_id: string | null;
  tags: Tag[];
  trade_notes: TradeNote[];
  created_at: string;
  updated_at: string;
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
  notes?: string | null;
  account_id?: string | null;
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
}

export interface PnlBySymbol {
  symbol: string;
  pnl: string;
  trade_count: number;
}

export interface PnlByAssetClass {
  asset_class: AssetClass;
  pnl: string;
  trade_count: number;
}
