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

import React, { useState } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeFilterBar } from "@/components/trades/TradeFilterBar";
import type { TradeFilters } from "@/hooks/useTrades";
import type { SavedTradeFilterRead } from "@/lib/types";

jest.mock("@/hooks/useActivePortfolio", () => ({
  useActivePortfolio: () => ({ activePortfolioId: "portfolio-1", isLoading: false }),
}));

jest.mock("@/hooks/useAccounts", () => ({
  useAccounts: () => ({ data: [{ id: "account-1", name: "IBKR Main", account_number: "U123" }], isLoading: false }),
}));

jest.mock("@/hooks/useTaxonomies", () => ({
  useGetTaxonomies: () => ({ data: [{ id: "tag-1", name: "FOMO", color_hex: "#22c55e" }] }),
}));

jest.mock("@/hooks/usePlaybooks", () => ({
  usePlaybooks: () => ({ data: [{ id: "playbook-1", name: "Breakout" }] }),
}));

jest.mock("@/hooks/useAnnotationDefinitions", () => ({
  useGetAnnotationDefinitions: () => ({ data: [{ id: "annotation-1", name: "Followed plan", scope: "trades", is_archived: false, type: "bool" }] }),
}));

function FilterBarHarness({ filters: initialFilters, onChange, ...props }: React.ComponentProps<typeof TradeFilterBar>) {
  const [filters, setFilters] = useState(initialFilters);
  return <TradeFilterBar {...props} filters={filters} onChange={(next) => {
    setFilters(next);
    onChange(next);
  }} />;
}

const userView: SavedTradeFilterRead = {
  id: "view-1", name: "Swing A+", scope: "USER", owner_id: "user-1", definition: {}, needs_review: false,
  created_at: "2026-10-24T12:00:00Z", updated_at: "2026-10-24T12:00:00Z",
};

describe("TradeFilterBar", () => {
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

  it("renders and toggles desktop execution-state values", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<FilterBarHarness filters={baseFilters} onChange={onChange} />);

    await user.click(within(screen.getByTestId("trade-desktop-filter-toolbar")).getByRole("button", { name: "Filter" }));
    const desktop = within(screen.getByTestId("trade-desktop-filters"));
    await user.click(desktop.getByRole("button", { name: "Edited" }));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ execution_state: ["edited"] })
    );
    expect(desktop.getByRole("button", { name: "Edited" })).toHaveAttribute("aria-pressed", "true");
    await user.click(desktop.getByRole("button", { name: "Edited" }));
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ execution_state: undefined }));
  });

  it("toggles the desktop unresolved execution-linking checkbox", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<FilterBarHarness filters={baseFilters} onChange={onChange} />);

    await user.click(within(screen.getByTestId("trade-desktop-filter-toolbar")).getByRole("button", { name: "Filter" }));
    const checkbox = within(screen.getByTestId("trade-desktop-filters")).getByRole("checkbox", { name: "Show only trades with unresolved execution linking" });
    await user.click(checkbox);

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ has_unlinked_executions: true })
    );
    await user.click(checkbox);
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ has_unlinked_executions: undefined }));
  });

  it("counts has_unlinked_executions as an active filter", () => {
    const onChange = jest.fn();
    render(
      <TradeFilterBar
        filters={{ ...baseFilters, has_unlinked_executions: true }}
        onChange={onChange}
      />
    );

    expect(within(screen.getByTestId("trade-desktop-filter-toolbar")).getByRole("button", { name: "Filter 1" })).toBeInTheDocument();
    expect(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: /Filter.*\(1\)/ })).toBeInTheDocument();
  });

  it("keeps the desktop panel toggle independent of the mobile dialog", async () => {
    const user = userEvent.setup();
    render(<TradeFilterBar filters={baseFilters} onChange={jest.fn()} />);
    const desktop = within(screen.getByTestId("trade-desktop-filter-toolbar"));

    expect(screen.queryByTestId("trade-desktop-filters")).not.toBeInTheDocument();
    await user.click(desktop.getByRole("button", { name: "Filter" }));
    expect(screen.getByTestId("trade-desktop-filters")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(desktop.getByRole("button", { name: "Filter" }));
    expect(screen.queryByTestId("trade-desktop-filters")).not.toBeInTheDocument();
  });

  it("applies mobile result changes live to onChange and the mounted desktop fields", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<FilterBarHarness filters={{ ...baseFilters, direction: "LONG" }} onChange={onChange} />);
    const desktopDirection = within(screen.getByTestId("trade-desktop-filters")).getByRole("combobox", { name: "Direction" });
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: /Filter/ }));
    const dialog = within(screen.getByRole("dialog", { name: "Filters" }));

    await user.click(dialog.getByRole("radio", { name: "Winners" }));
    expect(onChange).toHaveBeenLastCalledWith({ ...baseFilters, direction: "LONG", pnl_positive: true });
    expect(dialog.getByRole("tab", { name: "Trade 2" })).toHaveAttribute("aria-selected", "true");
    await user.selectOptions(dialog.getByRole("combobox", { name: "Direction" }), "SHORT");
    expect(onChange).toHaveBeenLastCalledWith({ ...baseFilters, direction: "SHORT", pnl_positive: true });
    expect(desktopDirection).toHaveValue("SHORT");
    expect(screen.getByRole("dialog", { name: "Filters" })).toBeInTheDocument();

    const changesBeforeClose = onChange.mock.calls.length;
    await user.click(dialog.getByRole("button", { name: "Show results" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(onChange).toHaveBeenCalledTimes(changesBeforeClose);
    expect(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: /Filter.*\(2\)/ })).toBeInTheDocument();
  });

  it("supports included/excluded symbols and asset-class filters inside the sheet", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<FilterBarHarness filters={baseFilters} onChange={onChange} />);
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: "Filter" }));
    const dialog = within(screen.getByRole("dialog", { name: "Filters" }));

    await user.type(dialog.getByRole("textbox", { name: "Symbol" }), "aapl,!tsla{Enter}");
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ symbols: ["AAPL"], excluded_symbols: ["TSLA"] }));
    await user.click(dialog.getByRole("button", { name: "COMBO" }));
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ symbols: ["AAPL"], excluded_symbols: ["TSLA"], asset_classes: ["COMBO"] }));
    expect(dialog.getByRole("tab", { name: "Trade 3" })).toBeInTheDocument();
  });

  it("applies midnight and Monday filters from the Time tab without losing trade filters", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<FilterBarHarness filters={{ ...baseFilters, pnl_positive: false }} onChange={onChange} />);
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: /Filter/ }));
    const dialog = within(screen.getByRole("dialog", { name: "Filters" }));
    await user.click(dialog.getByRole("tab", { name: "Time" }));

    await user.selectOptions(dialog.getByRole("combobox", { name: "Hour of Day" }), "0");
    await user.selectOptions(dialog.getByRole("combobox", { name: "Day of Week" }), "0");
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ hour_of_day: 0, day_of_week: 0, pnl_positive: false }));
    expect(dialog.getByRole("tab", { name: "Time 2" })).toBeInTheDocument();
    expect(dialog.getByRole("tab", { name: "Trade 1" })).toBeInTheDocument();
    for (const label of ["Opened From", "Opened To", "Closed From", "Closed To"]) {
      expect(dialog.getByLabelText(label)).toBeInTheDocument();
    }
  });

  it("edits playbook, taxonomy and annotation filters from the Journal tab", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    const annotationFilter = { annotation_definition_id: "annotation-1", operator: "eq", value: true, logic: "and" as const };
    render(<FilterBarHarness filters={{ ...baseFilters, annotation_filters: [annotationFilter] }} onChange={onChange} />);
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: /Filter/ }));
    const dialog = within(screen.getByRole("dialog", { name: "Filters" }));
    await user.click(dialog.getByRole("tab", { name: "Journal 1" }));

    await user.selectOptions(dialog.getByRole("combobox", { name: "Playbook" }), "playbook-1");
    await user.click(dialog.getByRole("button", { name: "FOMO" }));
    await user.selectOptions(dialog.getByRole("combobox", { name: "Followed plan value" }), "false");

    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ playbook_id: "playbook-1", taxonomy_ids: ["tag-1"], annotation_filters: [{ ...annotationFilter, value: false }] }));
    expect(dialog.getByRole("tab", { name: "Journal 3" })).toHaveAttribute("aria-selected", "true");
  });

  it("applies account selection, execution state and linking filters from the Account tab", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<FilterBarHarness filters={baseFilters} onChange={onChange} />);
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: "Filter" }));
    const dialog = within(screen.getByRole("dialog", { name: "Filters" }));
    await user.click(dialog.getByRole("tab", { name: "Account" }));
    await user.click(dialog.getByRole("button", { name: "Account" }));
    await user.click(dialog.getByRole("button", { name: "IBKR Main (U123)" }));
    await user.click(dialog.getByRole("button", { name: "Edited" }));
    await user.click(dialog.getByRole("checkbox", { name: "Show only trades with unresolved execution linking" }));

    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ account_ids: ["account-1"], execution_state: ["edited"], has_unlinked_executions: true }));
    expect(dialog.getByRole("tab", { name: "Account 3" })).toHaveAttribute("aria-selected", "true");
    await user.click(dialog.getByRole("button", { name: "Account" }));
    await user.click(dialog.getByRole("button", { name: "Clear selection" }));
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ account_ids: undefined, execution_state: ["edited"], has_unlinked_executions: true }));
  });

  it("clears every group live from the sheet without closing it", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<FilterBarHarness filters={{ ...baseFilters, symbols: ["AAPL"], excluded_symbols: ["TSLA"], hour_of_day: 0, playbook_id: "playbook-1", account_ids: ["account-1"], has_unlinked_executions: true }} onChange={onChange} />);
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: /Filter/ }));

    await user.click(screen.getByRole("button", { name: "Clear all" }));

    expect(onChange).toHaveBeenLastCalledWith(baseFilters);
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Trade", "Time", "Journal", "Account"]);
    expect(screen.getByRole("dialog", { name: "Filters" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show results" }));
    const mobile = within(screen.getByTestId("trade-mobile-filter-toolbar"));
    expect(mobile.getByRole("button", { name: "Filter" })).toBeInTheDocument();
    expect(mobile.queryByRole("button", { name: "Clear" })).not.toBeInTheDocument();
  });

  it("shows the saved-view name and clears filters from the mobile trigger row", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    render(<FilterBarHarness filters={{ ...baseFilters, direction: "LONG" }} onChange={onChange} activeView={userView} />);
    const mobile = within(screen.getByTestId("trade-mobile-filter-toolbar"));

    expect(mobile.getByText("Swing A+")).toBeInTheDocument();
    await user.click(mobile.getByRole("button", { name: "Clear" }));
    expect(onChange).toHaveBeenLastCalledWith(baseFilters);
    expect(mobile.getByRole("button", { name: "Filter" })).toBeInTheDocument();
    expect(mobile.queryByRole("button", { name: "Clear" })).not.toBeInTheDocument();
  });

  it.each([
    ["Save View", "onSaveView"], ["Update", "onUpdateView"], ["Rename", "onRenameView"], ["Delete View", "onDeleteView"],
  ] as const)("shares the %s callback between desktop and mobile", async (name, callback) => {
    const user = userEvent.setup();
    const actions = { onSaveView: jest.fn(), onUpdateView: jest.fn(), onRenameView: jest.fn(), onDeleteView: jest.fn() };
    render(<TradeFilterBar filters={baseFilters} onChange={jest.fn()} activeView={userView} {...actions} />);

    await user.click(within(screen.getByTestId("trade-desktop-filter-toolbar")).getByRole("button", { name }));
    expect(actions[callback]).toHaveBeenCalledTimes(1);
    await user.click(within(screen.getByTestId("trade-mobile-filter-toolbar")).getByRole("button", { name: "Filter" }));
    await user.click(within(screen.getByRole("dialog", { name: "Filters" })).getByRole("button", { name }));
    expect(actions[callback]).toHaveBeenCalledTimes(2);
  });
});
