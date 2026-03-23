import React from 'react';
import { DailyTradeData } from './types';
import { MonthView } from './MonthView';
import { addMonths, format } from 'date-fns';

interface MultiMonthViewProps {
  currentDate: Date;
  data: DailyTradeData[];
  currencySymbol: string;
  monthsToShow?: number;
  onDayClick?: (date: string) => void;
}

export const MultiMonthView: React.FC<MultiMonthViewProps> = ({
  currentDate,
  data,
  currencySymbol,
  monthsToShow = 3,
  onDayClick,
}) => {
  const months = Array.from({ length: monthsToShow }, (_, i) => addMonths(currentDate, i));

  return (
    <div className="flex flex-col gap-8">
      {months.map(month => (
        <div key={month.toString()}>
          <h2 className="text-lg font-semibold mb-3 text-foreground">
            {format(month, 'MMMM yyyy')}
          </h2>
          <MonthView
            currentDate={month}
            data={data}
            currencySymbol={currencySymbol}
            onDayClick={onDayClick}
          />
        </div>
      ))}
    </div>
  );
};
