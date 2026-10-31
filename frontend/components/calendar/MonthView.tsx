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

import React from 'react';
import { DailyTradeData } from './types';
import {
  format,
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  addDays,
} from 'date-fns';

interface MonthViewProps {
  currentDate: Date;
  data: DailyTradeData[];
  currencySymbol: string;
  onDayClick?: (date: string) => void;
}

export const MonthView: React.FC<MonthViewProps> = ({
  currentDate,
  data,
  currencySymbol,
  onDayClick,
}) => {
  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(currentDate);
  const startDate = startOfWeek(monthStart, { weekStartsOn: 0 }); // Sunday
  const endDate = endOfWeek(monthEnd, { weekStartsOn: 0 }); // Saturday

  const dateFormat = 'd';
  const rows: Date[][] = [];

  let days = [];
  let day = startDate;
  const formattedDate = '';

  while (day <= endDate) {
    for (let i = 0; i < 7; i++) {
      days.push(day);
      day = addDays(day, 1);
    }
    rows.push(days);
    days = [];
  }

  // Create lookup dictionary for O(1) access
  const tradeDataMap = data.reduce((acc, current) => {
    acc[current.date] = current;
    return acc;
  }, {} as Record<string, DailyTradeData>);

  const getCellClassName = (day: Date, pnl: number, tradeCount: number) => {
    if (!isSameMonth(day, monthStart)) {
      return 'bg-muted/30 text-muted-foreground/50'; // Out of month
    }
    
    if (tradeCount === 0) {
      return 'bg-card text-foreground'; // No trades, dark gray
    }
    
    if (pnl > 0) {
      return 'bg-teal-500/10 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400 border border-teal-500/30'; // Positive P&L
    }
    
    if (pnl < 0) {
      return 'bg-red-500/10 dark:bg-red-500/20 text-red-700 dark:text-red-400 border border-red-500/30'; // Negative P&L
    }

    return 'bg-card text-foreground'; // Break-even or other
  };

  return (
    <div className="w-full bg-card rounded-lg border border-border overflow-hidden">
      {/* Header Row */}
      <div className="grid grid-cols-8 border-b border-border bg-muted/30">
        {['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'].map((dayName, index) => (
          <div key={index} className="py-2 text-center text-xs font-semibold text-muted-foreground border-r border-border last:border-r-0">
            {dayName}
          </div>
        ))}
        <div className="py-2 text-center text-xs font-semibold text-muted-foreground bg-muted/50">
          SUMMARY
        </div>
      </div>

      {/* Grid */}
      <div className="flex flex-col">
        {rows.map((row, rowIndex) => {
          let weekPnL = 0;
          let weekTrades = 0;

          // Calculate week summary
          row.forEach(day => {
            const dateStr = format(day, 'yyyy-MM-dd');
            const dayData = tradeDataMap[dateStr];
            if (dayData && isSameMonth(day, monthStart)) {
              weekPnL += dayData.pnl;
              weekTrades += dayData.tradeCount;
            }
          });

          return (
            <div key={rowIndex} className="grid grid-cols-8 border-b border-border last:border-b-0">
              {/* Days */}
              {row.map((day, dayIndex) => {
                const dateStr = format(day, 'yyyy-MM-dd');
                const dayData = tradeDataMap[dateStr] || { date: dateStr, pnl: 0, tradeCount: 0 };
                
                const isClickable = dayData.tradeCount > 0 && isSameMonth(day, monthStart) && !!onDayClick;
                return (
                  <div
                    key={dayIndex}
                    onClick={isClickable ? () => onDayClick!(dateStr) : undefined}
                    className={`min-h-[100px] p-2 border-r border-border last:border-r-0 flex flex-col transition-colors
                      ${getCellClassName(day, dayData.pnl, dayData.tradeCount)}
                      ${isClickable ? 'cursor-pointer hover:brightness-125 hover:ring-1 hover:ring-inset hover:ring-white/20' : ''}`}
                  >
                    <div className="flex justify-between items-start">
                      <span className={`text-sm font-medium ${isSameDay(day, new Date()) ? 'bg-accent text-white px-1.5 rounded-sm' : ''}`}>
                        {format(day, dateFormat)}
                      </span>
                      {dayData.tradeCount > 0 && isSameMonth(day, monthStart) && (
                        <span className="text-[10px] bg-zinc-100/50 dark:bg-zinc-900/50 px-1 rounded text-muted-foreground">
                          {dayData.tradeCount} trades
                        </span>
                      )}
                    </div>
                    
                    {dayData.tradeCount > 0 && isSameMonth(day, monthStart) && (
                      <div className="mt-auto pt-2 flex justify-end">
                        <span className="font-bold text-sm">
                          {dayData.pnl > 0 ? '+' : ''}{currencySymbol}{Math.abs(dayData.pnl).toFixed(2)}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
              
              {/* Week Summary Column */}
              <div className={`min-h-[100px] p-2 flex flex-col justify-center items-end border-l-2 border-border/50
                ${weekTrades === 0 ? 'bg-muted/10' : weekPnL > 0 ? 'bg-teal-500/10 text-teal-700 dark:text-teal-400' : 'bg-red-500/10 text-red-700 dark:text-red-400'}`
              }>
                {weekTrades > 0 ? (
                  <>
                    <span className="text-xs text-muted-foreground mb-1">
                      {weekTrades} trades
                    </span>
                    <span className="font-bold">
                      {weekPnL > 0 ? '+' : ''}{currencySymbol}{Math.abs(weekPnL).toFixed(2)}
                    </span>
                  </>
                ) : (
                  <span className="text-xs text-muted-foreground">-</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
