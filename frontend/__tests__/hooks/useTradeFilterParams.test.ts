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

import { renderHook } from "@testing-library/react";
import { useTradeFilterParams } from "@/hooks/useTradeFilterParams";

const mockGet = jest.fn();

jest.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (key: string) => mockGet(key),
    toString: () => "",
  }),
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

describe("useTradeFilterParams execution_state", () => {
  it("parses execution_state from URL params", () => {
    mockGet.mockImplementation((key: string) => {
      if (key === "execution_state") return "manual,edited";
      return null;
    });

    const { result } = renderHook(() => useTradeFilterParams());

    expect(result.current.filters.execution_state).toEqual(["manual", "edited"]);
  });
});
