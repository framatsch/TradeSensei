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
