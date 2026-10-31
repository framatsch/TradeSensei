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
import { TradeFilterSheet } from "@/components/trades/TradeFilterSheet";
import type { TradeFilters } from "@/hooks/useTrades";
import type { SavedTradeFilterRead } from "@/lib/types";

type SheetProps = React.ComponentProps<typeof TradeFilterSheet>;

const userView: SavedTradeFilterRead = {
  id: "view-1", name: "Swing A+", scope: "USER", owner_id: "user-1", definition: {}, needs_review: false,
  created_at: "2026-10-24T12:00:00Z", updated_at: "2026-10-24T12:00:00Z",
};

const activeFilters: TradeFilters = {
  symbols: ["AAPL"], excluded_symbols: ["TSLA"], pnl_positive: false,
  hour_of_day: 0, day_of_week: 0,
  playbook_id: "playbook-1", taxonomy_ids: ["tag-1", "tag-2"],
  annotation_filters: [{ annotation_definition_id: "annotation-1", operator: "eq", value: false, logic: "and" }],
  account_ids: ["account-1", "account-2"], execution_state: ["manual", "edited"], has_unlinked_executions: true,
};

function ControlledSheet(props: SheetProps) {
  const [open, setOpen] = useState(props.open);
  return <TradeFilterSheet {...props} open={open} onOpenChange={(value) => {
    setOpen(value);
    props.onOpenChange(value);
  }} />;
}

function renderSheet(overrides: Partial<SheetProps> = {}) {
  const props: SheetProps = {
    open: true,
    onOpenChange: jest.fn(),
    filters: {},
    renderField: (key) => <p>{key}</p>,
    onClear: jest.fn(),
    trigger: <button type="button">Open filters</button>,
    ...overrides,
  };
  return { ...render(<ControlledSheet {...props} />), props };
}

describe("TradeFilterSheet", () => {
  it("shows per-group counts, including excluded symbols, false and zero values", () => {
    renderSheet({ filters: activeFilters });
    const dialog = within(screen.getByRole("dialog", { name: "Filters" }));

    expect(dialog.getByRole("tab", { name: "Trade 3" })).toHaveAttribute("aria-selected", "true");
    expect(dialog.getByRole("tab", { name: "Time 2" })).toHaveAttribute("aria-selected", "false");
    expect(dialog.getByRole("tab", { name: "Journal 3" })).toHaveAttribute("aria-selected", "false");
    expect(dialog.getByRole("tab", { name: "Account 3" })).toHaveAttribute("aria-selected", "false");
    expect(dialog.getByRole("tabpanel", { name: "Trade 3" })).toHaveTextContent("symbols");
    expect(dialog.queryByText("hour_of_day")).not.toBeInTheDocument();
  });

  it("renders only the chosen group's fields with linked tab/panel semantics", async () => {
    const user = userEvent.setup();
    renderSheet();

    for (const [tab, fields] of [
      ["Time", ["opened_at_from", "opened_at_to", "closed_at_from", "closed_at_to", "hour_of_day", "day_of_week"]],
      ["Journal", ["playbook_id", "taxonomy_ids", "annotation_filters"]],
      ["Account", ["account_ids", "execution_state", "has_unlinked_executions"]],
      ["Trade", ["symbols", "direction", "status", "pnl_positive", "asset_classes"]],
    ] as const) {
      const tabButton = screen.getByRole("tab", { name: tab });
      await user.click(tabButton);
      const panel = screen.getByRole("tabpanel", { name: tab });
      expect(tabButton).toHaveAttribute("aria-selected", "true");
      expect(tabButton).toHaveAttribute("aria-controls", panel.id);
      expect(panel).toHaveAttribute("aria-labelledby", tabButton.id);
      expect(within(panel).getAllByRole("paragraph").map((field) => field.textContent)).toEqual(fields);
      expect(screen.getAllByRole("tabpanel")).toHaveLength(1);
    }
  });

  it("supports arrow, Home and End keys with roving tab focus", async () => {
    const user = userEvent.setup();
    renderSheet();
    await user.click(screen.getByRole("tab", { name: "Trade" }));

    for (const [key, name] of [
      ["{ArrowRight}", "Time"], ["{End}", "Account"], ["{ArrowRight}", "Trade"],
      ["{ArrowLeft}", "Account"], ["{Home}", "Trade"],
    ]) {
      await user.keyboard(key);
      const tab = screen.getByRole("tab", { name });
      expect(tab).toHaveFocus();
      expect(tab).toHaveAttribute("aria-selected", "true");
      expect(tab).toHaveAttribute("tabindex", "0");
    }
  });

  it("forwards field changes immediately and updates counts without closing", async () => {
    const user = userEvent.setup();
    const onChange = jest.fn();
    const onOpenChange = jest.fn();
    function LiveFilters() {
      const [filters, setFilters] = useState<TradeFilters>({});
      return <TradeFilterSheet open onOpenChange={onOpenChange} filters={filters} onClear={jest.fn()} renderField={(key) => key === "pnl_positive" ? (
        <label><input type="radio" checked={filters.pnl_positive === true} onChange={() => {
          const next = { ...filters, pnl_positive: true };
          onChange(next);
          setFilters(next);
        }} />Winners</label>
      ) : null} />;
    }
    render(<LiveFilters />);

    await user.click(screen.getByRole("radio", { name: "Winners" }));

    expect(onChange).toHaveBeenCalledWith({ pnl_positive: true });
    expect(screen.getByRole("tab", { name: "Trade 1" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("dialog", { name: "Filters" })).toBeInTheDocument();
    expect(onOpenChange).not.toHaveBeenCalled();
  });

  it("delegates Clear all without dismissing and removes all badges when filters reset", async () => {
    const user = userEvent.setup();
    const { props, rerender } = renderSheet({ filters: activeFilters });
    await user.click(screen.getByRole("button", { name: "Clear all" }));

    expect(props.onClear).toHaveBeenCalledTimes(1);
    expect(props.onOpenChange).not.toHaveBeenCalled();
    rerender(<ControlledSheet {...props} filters={{}} />);

    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Trade", "Time", "Journal", "Account"]);
    expect(screen.getByRole("dialog", { name: "Filters" })).toBeInTheDocument();
  });

  it.each(["Close filters", "Show results"])("dismisses using %s without changing filters", async (name) => {
    const user = userEvent.setup();
    const { props } = renderSheet({ filters: activeFilters });
    await user.click(screen.getByRole("button", { name }));

    expect(props.onOpenChange).toHaveBeenCalledWith(false);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(props.onClear).not.toHaveBeenCalled();
  });

  it("closes with Escape and resets to Trade when reopened from the trigger", async () => {
    const user = userEvent.setup();
    const { props } = renderSheet({ open: false });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open filters" }));
    await user.click(screen.getByRole("tab", { name: "Journal" }));
    await user.keyboard("{Escape}");

    expect(props.onOpenChange).toHaveBeenLastCalledWith(false);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open filters" }));
    expect(screen.getByRole("tab", { name: "Trade" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Trade" })).toBeInTheDocument();
  });

  it.each([
    ["Save View", "onSaveView", true],
    ["Update", "onUpdateView", false],
    ["Rename", "onRenameView", true],
    ["Delete View", "onDeleteView", false],
  ] as const)("delegates %s to the saved-view callback", async (name, callback, closes) => {
    const user = userEvent.setup();
    const actions = { onSaveView: jest.fn(), onUpdateView: jest.fn(), onRenameView: jest.fn(), onDeleteView: jest.fn() };
    const { props } = renderSheet({ activeView: userView, ...actions });

    await user.click(screen.getByRole("button", { name }));

    expect(actions[callback]).toHaveBeenCalledTimes(1);
    for (const key of Object.keys(actions) as (keyof typeof actions)[]) {
      if (key !== callback) expect(actions[key]).not.toHaveBeenCalled();
    }
    if (closes) {
      expect(props.onOpenChange).toHaveBeenCalledWith(false);
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    } else {
      expect(props.onOpenChange).not.toHaveBeenCalled();
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    }
  });

  it.each([undefined, { ...userView, scope: "SYSTEM" as const }])("only offers Save View for an absent or system view", (activeView) => {
    renderSheet({ activeView, onSaveView: jest.fn(), onUpdateView: jest.fn(), onRenameView: jest.fn(), onDeleteView: jest.fn() });

    expect(screen.getByRole("button", { name: "Save View" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Update" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rename" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete View" })).not.toBeInTheDocument();
  });

  it("disables Update while the saved view is being persisted", async () => {
    const user = userEvent.setup();
    const onUpdateView = jest.fn();
    renderSheet({ activeView: userView, onUpdateView, isUpdating: true });
    const update = screen.getByRole("button", { name: "Updating…" });

    expect(update).toBeDisabled();
    await user.click(update);
    expect(onUpdateView).not.toHaveBeenCalled();
  });
});
