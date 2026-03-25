import React from 'react';
import { DailyTradeData } from './types';
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, isSameMonth, setMonth } from 'date-fns';

interface YearViewProps {
  currentDate: Date;
  data: DailyTradeData[];
  currencySymbol: string;
  onDayClick?: (date: string) => void;
}

export const YearView: React.FC<YearViewProps> = ({
  currentDate,
  data,
  currencySymbol,
  onDayClick,
}) => {
  const currentYear = currentDate.getFullYear();
  const months = Array.from({ length: 12 }, (_, i) => {
    const d = new Date(currentYear, i, 1);
    return d;
  });

  const tradeDataMap = data.reduce((acc, current) => {
    acc[current.date] = current;
    return acc;
  }, {} as Record<string, DailyTradeData>);

  const renderMiniMonth = (monthDate: Date) => {
    const monthStart = startOfMonth(monthDate);
    const monthEnd = endOfMonth(monthDate);
    const startDate = startOfWeek(monthStart, { weekStartsOn: 0 });
    const endDate = endOfWeek(monthEnd, { weekStartsOn: 0 });

    const rows: Date[][] = [];
    let days = [];
    let day = startDate;

    while (day <= endDate) {
      for (let i = 0; i < 7; i++) {
        days.push(day);
        day = addDays(day, 1);
      }
      rows.push(days);
      days = [];
    }

    let monthPnL = 0;
    let monthTrades = 0;

    return (
      <div key={monthDate.toString()} className="bg-card border border-border rounded-lg p-3">
        <h3 className="text-sm font-semibold mb-2 flex justify-between items-center text-foreground">
          <span>{format(monthDate, 'MMMM')}</span>
        </h3>
        
        <div className="grid grid-cols-7 gap-0.5 mb-1">
          {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((d, i) => (
            <div key={i} className="text-[10px] text-center text-muted-foreground">
              {d}
            </div>
          ))}
        </div>
        
        <div className="flex flex-col gap-0.5">
          {rows.map((row, rowIndex) => (
            <div key={rowIndex} className="grid grid-cols-7 gap-0.5">
              {row.map((d, dayIndex) => {
                const dateStr = format(d, 'yyyy-MM-dd');
                const dayData = tradeDataMap[dateStr];
                const isCurrentMonth = isSameMonth(d, monthStart);
                
                if (isCurrentMonth && dayData) {
                  monthPnL += dayData.pnl;
                  monthTrades += dayData.tradeCount;
                }

                let cellClass = "aspect-square rounded-sm flex items-center justify-center text-[10px] ";
                
                if (!isCurrentMonth) {
                  cellClass += "opacity-0"; // hide days not in month for mini view
                } else if (!dayData || dayData.tradeCount === 0) {
                  cellClass += "bg-muted/30 text-muted-foreground";
                } else if (dayData.pnl > 0) {
                  cellClass += "bg-teal-500/20 text-teal-700 dark:bg-teal-500/40 dark:text-teal-100";
                } else if (dayData.pnl < 0) {
                  cellClass += "bg-red-500/20 text-red-700 dark:bg-red-500/40 dark:text-red-100";
                }

                const isClickable = isCurrentMonth && !!dayData && dayData.tradeCount > 0 && !!onDayClick;
                return (
                  <div
                    key={dayIndex}
                    onClick={isClickable ? () => onDayClick!(dateStr) : undefined}
                    className={cellClass + (isClickable ? ' cursor-pointer hover:brightness-125' : '')}
                  >
                    {isCurrentMonth ? format(d, 'd') : ''}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        
        <div className="mt-3 pt-2 border-t border-border flex justify-between items-center text-xs">
          <span className="text-muted-foreground">{monthTrades} trades</span>
          <span className={`font-medium ${monthPnL > 0 ? 'text-teal-600 dark:text-teal-400' : monthPnL < 0 ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'}`}>
            {monthPnL > 0 ? '+' : ''}{currencySymbol}{Math.abs(monthPnL).toFixed(2)}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {months.map(month => renderMiniMonth(month))}
    </div>
  );
};
