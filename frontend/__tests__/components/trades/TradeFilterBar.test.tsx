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

import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { TradeFilterBar } from "@/components/trades/TradeFilterBar";
import type { TradeFilters } from "@/hooks/useTrades";

jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: () => ({ activePortfolioId: "portfolio-1", isLoading: false }),
}));

jest.mock("@/hooks/useAccounts", () => ({
  useAccounts: () => ({ data: [], isLoading: false }),
}));

jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: () => ({ data: [] }),
}));

jest.mock("@/hooks/usePlaybooks", () => ({
  usePlaybooks: () => ({ data: [] }),
}));

jest.mock("@/hooks/useAnnotationDefinitions", () => ({
  useGetAnnotationDefinitions: () => ({ data: [] }),
}));

describe("TradeFilterBar execution_state filter", () => {
  const baseFilters: TradeFilters = {
    symbols: [],
    excluded_symbols: [],
    direction: "",
    asset_classes: [],
    opened_at_from: "",
    opened_at_to: "",
    closed_at_from: "",
    closed_at_to: "",
    taxonomy_ids: [],
    account_ids: [],
    playbook_id: "",
    pnl_positive: null,
    status: null,
    hour_of_day: undefined,
    day_of_week: undefined,
    annotation_filters: [],
    execution_state: [],
    has_unlinked_executions: undefined,
  };

  it("renders and toggles execution_state values", () => {
    const onChange = jest.fn();
    render(
      <TradeFilterBar
        filters={baseFilters}
        onChange={onChange}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    fireEvent.click(screen.getByRole("button", { name: "Edited" }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ execution_state: ["edited"] })
    );
  });

  it("toggles has_unlinked_executions checkbox", () => {
    const onChange = jest.fn();
    render(
      <TradeFilterBar
        filters={baseFilters}
        onChange={onChange}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    fireEvent.click(screen.getByLabelText("Show only flagged trades"));

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ has_unlinked_executions: true })
    );
  });

  it("counts has_unlinked_executions as an active filter", () => {
    const onChange = jest.fn();
    render(
      <TradeFilterBar
        filters={{ ...baseFilters, has_unlinked_executions: true }}
        onChange={onChange}
      />
    );

    expect(screen.getByText("1")).toBeInTheDocument();
  });
});
