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
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TradeNavControls, TradePositionIndicator } from "@/components/trades/TradeNavControls";
import type { useTradeNavigation } from "@/hooks/useTradeNavigation";

type Navigation = ReturnType<typeof useTradeNavigation>;

function makeNavigation(overrides: Partial<Navigation> = {}): Navigation {
  return {
    available: true,
    prevId: "trade-24",
    nextId: "trade-26",
    canGoPrev: true,
    canGoNext: true,
    prevSymbol: "MSFT",
    nextSymbol: "TSLA",
    position: 25,
    total: 128,
    sourceLabel: "View: Swing A+",
    isLoadingNext: false,
    navigationError: null,
    goPrev: jest.fn(),
    goNext: jest.fn().mockResolvedValue(undefined),
    backHref: "/dashboard/trades?view_id=swing",
    ...overrides,
  };
}

describe("TradeNavControls", () => {
  it("renders desktop labels, adjacent-symbol shortcut tooltips, and position 25 / 128 with its source", () => {
    render(<TradeNavControls navigation={makeNavigation()} />);

    expect(screen.getByRole("button", { name: "Previous trade" })).toHaveTextContent("Previous");
    expect(screen.getByRole("button", { name: "Next trade" })).toHaveTextContent("Next");
    expect(screen.getByRole("button", { name: "Previous trade" })).toHaveAttribute("title", "Previous: MSFT (←)");
    expect(screen.getByRole("button", { name: "Next trade" })).toHaveAttribute("title", "Next: TSLA (→)");
    expect(screen.getByText("25 / 128")).toHaveAttribute("title", "Position in your filtered trade list (View: Swing A+)");
  });

  it("calls the navigation handlers when the enabled buttons are clicked", async () => {
    const user = userEvent.setup();
    const navigation = makeNavigation();
    render(<TradeNavControls navigation={navigation} />);

    await user.click(screen.getByRole("button", { name: "Previous trade" }));
    await user.click(screen.getByRole("button", { name: "Next trade" }));

    expect(navigation.goPrev).toHaveBeenCalledTimes(1);
    expect(navigation.goNext).toHaveBeenCalledTimes(1);
  });

  it("keeps compact icon buttons accessible and leaves the position for the mobile header", () => {
    render(<TradeNavControls navigation={makeNavigation()} variant="compact" />);

    expect(screen.getByRole("button", { name: "Previous trade" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next trade" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Previous trade" })).not.toHaveTextContent("Previous");
    expect(screen.getByRole("button", { name: "Next trade" })).not.toHaveTextContent("Next");
    expect(screen.queryByText("25 / 128")).not.toBeInTheDocument();
  });

  it("renders neither controls nor a position indicator without an available list context", () => {
    const navigation = makeNavigation({ available: false });
    render(<><TradeNavControls navigation={navigation} /><TradePositionIndicator navigation={navigation} /></>);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByText("25 / 128")).not.toBeInTheDocument();
  });

  it.each(["first", "last", "only"] as const)("disables the unavailable buttons at the %s trade boundary", async (boundary) => {
    const user = userEvent.setup();
    const navigation = makeNavigation({ canGoPrev: boundary === "last", canGoNext: boundary === "first" });
    render(<TradeNavControls navigation={navigation} />);
    const previous = screen.getByRole("button", { name: "Previous trade" });
    const next = screen.getByRole("button", { name: "Next trade" });

    if (!navigation.canGoPrev) {
      expect(previous).toBeDisabled();
      await user.click(previous);
    } else expect(previous).toBeEnabled();
    if (!navigation.canGoNext) {
      expect(next).toBeDisabled();
      await user.click(next);
    } else expect(next).toBeEnabled();

    expect(navigation.goPrev).not.toHaveBeenCalled();
    expect(navigation.goNext).not.toHaveBeenCalled();
  });

  it("shows loading and prevents either action while a next-page request is pending", async () => {
    const user = userEvent.setup();
    const navigation = makeNavigation({ isLoadingNext: true });
    render(<TradeNavControls navigation={navigation} />);

    expect(screen.getByLabelText("Loading next trades")).toBeInTheDocument();
    const previous = screen.getByRole("button", { name: "Previous trade" });
    const next = screen.getByRole("button", { name: "Next trade" });
    expect(previous).toBeDisabled();
    expect(next).toBeDisabled();
    await user.click(previous);
    await user.click(next);

    expect(navigation.goPrev).not.toHaveBeenCalled();
    expect(navigation.goNext).not.toHaveBeenCalled();
  });

  it("retains shortcut tooltips when symbols are uncached and displays a dash for an unknown total", () => {
    render(<TradeNavControls navigation={makeNavigation({ prevSymbol: null, nextSymbol: null, total: null })} />);

    expect(screen.getByRole("button", { name: "Previous trade" })).toHaveAttribute("title", "Previous (←)");
    expect(screen.getByRole("button", { name: "Next trade" })).toHaveAttribute("title", "Next (→)");
    expect(screen.getByText("25 / —")).toBeInTheDocument();
  });

  it("announces the boundary error and allows the user to retry with Next", async () => {
    const user = userEvent.setup();
    const navigation = makeNavigation({ navigationError: "Could not load the next trades. Please try again." });
    render(<TradeNavControls navigation={navigation} />);

    expect(screen.getByRole("alert")).toHaveTextContent(navigation.navigationError!);
    await user.click(screen.getByRole("button", { name: "Next trade" }));

    expect(navigation.goNext).toHaveBeenCalledTimes(1);
  });
});
