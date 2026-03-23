import React from 'react';
import { CalendarViewMode, DailyTradeData } from './types';
import { format, addMonths, subMonths, addYears, subYears } from 'date-fns';

interface CalendarHeaderProps {
  currentDate: Date;
  viewMode: CalendarViewMode;
  onDateChange: (date: Date) => void;
  onViewModeChange: (mode: CalendarViewMode) => void;
  currencySymbol: string;
  data: DailyTradeData[];
}

export const CalendarHeader: React.FC<CalendarHeaderProps> = ({
  currentDate,
  viewMode,
  onDateChange,
  onViewModeChange,
  currencySymbol,
  data
}) => {
  // Calculate total PnL based on view mode
  const currentMonthStr = format(currentDate, 'yyyy-MM');
  const currentYearStr = format(currentDate, 'yyyy');
  
  const filteredData = data.filter(d => {
    if (viewMode === 'month') {
      return d.date.startsWith(currentMonthStr);
    } else {
      return d.date.startsWith(currentYearStr);
    }
  });

  const totalPnL = filteredData.reduce((sum, d) => sum + d.pnl, 0);
  const totalTrades = filteredData.reduce((sum, d) => sum + d.tradeCount, 0);

  const handlePrev = () => {
    if (viewMode === 'month' || viewMode === 'multi-month') {
      onDateChange(subMonths(currentDate, 1));
    } else {
      onDateChange(subYears(currentDate, 1));
    }
  };

  const handleNext = () => {
    if (viewMode === 'month' || viewMode === 'multi-month') {
      onDateChange(addMonths(currentDate, 1));
    } else {
      onDateChange(addYears(currentDate, 1));
    }
  };

  const handleToday = () => {
    onDateChange(new Date());
  };

  const years = Array.from({ length: 11 }, (_, i) => new Date().getFullYear() - 5 + i);
  const months = Array.from({ length: 12 }, (_, i) => i);

  return (
    <div className="flex flex-col sm:flex-row justify-between items-center mb-6 gap-4">
      <div className="flex items-center gap-2">
        <button
          onClick={handleToday}
          className="px-3 py-1.5 text-sm font-medium bg-card text-foreground rounded-md border border-border hover:bg-muted transition-colors"
        >
          Today
        </button>
        
        <div className="flex items-center bg-card border border-border rounded-md overflow-hidden">
          <button
            onClick={handlePrev}
            className="px-3 py-1.5 hover:bg-muted transition-colors border-r border-border"
            aria-label="Previous"
          >
            &lt;
          </button>
          
          <div className="flex items-center px-2 gap-1">
            <select
              value={currentDate.getMonth()}
              onChange={(e) => {
                const newDate = new Date(currentDate);
                newDate.setMonth(parseInt(e.target.value));
                onDateChange(newDate);
              }}
              className="bg-transparent text-sm font-medium focus:outline-none cursor-pointer appearance-none"
            >
              {months.map(m => {
                const d = new Date();
                d.setMonth(m);
                return <option key={m} value={m} className="bg-card">{format(d, 'MMMM')}</option>;
              })}
            </select>
            
            <select
              value={currentDate.getFullYear()}
              onChange={(e) => {
                const newDate = new Date(currentDate);
                newDate.setFullYear(parseInt(e.target.value));
                onDateChange(newDate);
              }}
              className="bg-transparent text-sm font-medium focus:outline-none cursor-pointer appearance-none"
            >
              {years.map(y => (
                <option key={y} value={y} className="bg-card">{y}</option>
              ))}
            </select>
          </div>
          
          <button
            onClick={handleNext}
            className="px-3 py-1.5 hover:bg-muted transition-colors border-l border-border"
            aria-label="Next"
          >
            &gt;
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex bg-card border border-border rounded-md p-1">
          {(['month', 'year', 'multi-month'] as CalendarViewMode[]).map(mode => (
            <button
              key={mode}
              onClick={() => onViewModeChange(mode)}
              className={`px-3 py-1 text-sm rounded-sm capitalize transition-colors ${
                viewMode === mode 
                  ? 'bg-accent text-white shadow-sm' 
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`}
            >
              {mode.replace('-', ' ')}
            </button>
          ))}
        </div>

        <div className="flex flex-col items-end">
          <span className="text-xs text-muted-foreground uppercase tracking-wider">
            {viewMode === 'year' ? 'Year P&L' : 'Month P&L'}
          </span>
          <div className="flex items-baseline gap-2">
            <span className={`font-bold ${
              totalPnL > 0 ? 'text-teal-400' : totalPnL < 0 ? 'text-red-400' : 'text-muted-foreground'
            }`}>
              {totalPnL > 0 ? '+' : ''}{currencySymbol}{Math.abs(totalPnL).toFixed(2)}
            </span>
            <span className="text-xs text-muted-foreground">
              ({totalTrades} trades)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
