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

import { mapGeneratedExecution } from '@/hooks/useExecutions';
import type { LogicalExecution } from '@/lib/types';
import type { LogicalExecutionRead as GeneratedLogicalExecutionRead } from '@/lib/api/index';

describe('mapGeneratedExecution', () => {
  it('should map generated execution correctly', () => {
    const generated: GeneratedLogicalExecutionRead = {
      id: '123',
      trade_id: 't1',
      user_id: 'u1',
      account_id: 'a1',
      symbol: 'AAPL',
      asset_class: 'EQUITY',
      conid: '12345',  // IBKR contract IDs are strings
      direction: 'LONG',
      quantity: '10',
      price: '150',
      raw_quantity: '10',
      raw_price: '150',
      commission: '1',
      pnl: '100',
      pnl_eur: '90',
      executed_at: '2023-01-01T10:00:00Z',
      origin: 'imported',
      deleted: false,
      user_modified: false,
      parent_id: null,
      multiplier: 1,
      currency: 'USD',
      created_at: '2023-01-01T10:00:00Z',
      updated_at: '2023-01-01T10:00:00Z',
    };

    const result = mapGeneratedExecution(generated);

    const expected: LogicalExecution = {
      id: '123',
      trade_id: 't1',
      user_id: 'u1',
      account_id: 'a1',
      symbol: 'AAPL',
      asset_class: 'EQUITY',
      conid: '12345',
      direction: 'LONG',
      quantity: '10',
      price: '150',
      raw_quantity: '10',
      raw_price: '150',
      commission: '1',
      pnl: '100',
      pnl_eur: '90',
      executed_at: '2023-01-01T10:00:00Z',
      origin: 'imported',
      deleted: false,
      user_modified: false,
      parent_id: null,
      multiplier: 1,
      currency: 'USD',
      created_at: '2023-01-01T10:00:00Z',
      updated_at: '2023-01-01T10:00:00Z',
    };

    expect(result).toEqual(expected);
  });

  it('should handle missing optional fields', () => {
    const generated: GeneratedLogicalExecutionRead = {
      id: '123',
      user_id: 'u1',
      symbol: 'AAPL',
      asset_class: 'EQUITY',
      direction: 'LONG',
      quantity: '10',
      price: '150',
      raw_quantity: '10',
      raw_price: '150',
      executed_at: '2023-01-01T10:00:00Z',
      origin: 'manual',
      deleted: false,
      user_modified: true,
      multiplier: 1,
      created_at: '2023-01-01T10:00:00Z',
      updated_at: '2023-01-01T10:00:00Z',
    };

    const result = mapGeneratedExecution(generated);

    const expected: LogicalExecution = {
      id: '123',
      trade_id: null,
      user_id: 'u1',
      account_id: null,
      symbol: 'AAPL',
      asset_class: 'EQUITY',
      conid: null,
      direction: 'LONG',
      quantity: '10',
      price: '150',
      raw_quantity: '10',
      raw_price: '150',
      commission: '0',
      pnl: null,
      pnl_eur: null,
      executed_at: '2023-01-01T10:00:00Z',
      origin: 'manual',
      deleted: false,
      user_modified: true,
      parent_id: null,
      multiplier: 1,
      currency: null,
      created_at: '2023-01-01T10:00:00Z',
      updated_at: '2023-01-01T10:00:00Z',
    };

    expect(result).toEqual(expected);
  });

  it('should throw when called with undefined input', () => {
    // Documents that mapGeneratedExecution is not null-safe —
    // callers must verify data before invoking.
    expect(() => mapGeneratedExecution(undefined as unknown as GeneratedLogicalExecutionRead)).toThrow();
  });
});
