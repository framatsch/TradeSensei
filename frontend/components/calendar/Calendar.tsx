import React, { useState } from 'react';
import { CalendarProps, CalendarViewMode } from './types';
import { CalendarHeader } from './CalendarHeader';
import { MonthView } from './MonthView';
import { YearView } from './YearView';
import { MultiMonthView } from './MultiMonthView';

export const Calendar: React.FC<CalendarProps> = ({
  data,
  currencySymbol = '$',
  initialDate = new Date(),
  initialViewMode = 'month',
  onDayClick,
}) => {
  const [currentDate, setCurrentDate] = useState<Date>(initialDate);
  const [viewMode, setViewMode] = useState<CalendarViewMode>(initialViewMode);

  return (
    <div className="w-full flex flex-col">
      <CalendarHeader
        currentDate={currentDate}
        viewMode={viewMode}
        onDateChange={setCurrentDate}
        onViewModeChange={setViewMode}
        currencySymbol={currencySymbol}
        data={data}
      />

      <div className="w-full">
        {viewMode === 'month' && (
          <MonthView
            currentDate={currentDate}
            data={data}
            currencySymbol={currencySymbol}
            onDayClick={onDayClick}
          />
        )}
        
        {viewMode === 'year' && (
          <YearView
            currentDate={currentDate}
            data={data}
            currencySymbol={currencySymbol}
            onDayClick={onDayClick}
          />
        )}
        
        {viewMode === 'multi-month' && (
          <MultiMonthView
            currentDate={currentDate}
            data={data}
            currencySymbol={currencySymbol}
            monthsToShow={3}
            onDayClick={onDayClick}
          />
        )}
      </div>
    </div>
  );
};
