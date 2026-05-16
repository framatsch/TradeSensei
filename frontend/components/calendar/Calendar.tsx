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
