export interface DailyTradeData {
  date: string; // YYYY-MM-DD
  pnl: number;
  tradeCount: number;
}

export type CalendarViewMode = 'month' | 'year' | 'multi-month';

export interface CalendarProps {
  data: DailyTradeData[];
  currencySymbol?: string;
  initialDate?: Date;
  initialViewMode?: CalendarViewMode;
  /** Called when the user clicks a day cell that has at least one trade. */
  onDayClick?: (date: string) => void;
}
