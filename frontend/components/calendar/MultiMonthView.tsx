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
