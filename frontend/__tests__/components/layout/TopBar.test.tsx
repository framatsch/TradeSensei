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
import { TopBar } from "@/components/layout/TopBar";

jest.mock("next/navigation", () => ({
  usePathname: () => "/dashboard/trades",
}));

jest.mock("@/hooks/useAppContext", () => ({
  useAppContext: () => ({ activeContext: "portfolio" }),
}));

jest.mock("@/hooks/useSettings", () => ({
  useSettings: () => ({ data: { home_route: "/dashboard/trades" } }),
}));

jest.mock("@/components/layout/BentoMenu", () => ({
  BentoMenu: () => <button aria-label="Bento Menu">Bento</button>,
}));

jest.mock("@/components/layout/PortfolioSwitcher", () => ({
  PortfolioSwitcher: () => <div data-testid="portfolio-switcher">Portfolio</div>,
}));

jest.mock("@/components/layout/UserBadge", () => ({
  UserBadge: () => <div data-testid="user-badge">User</div>,
}));

describe("TopBar", () => {
  it("renders the Home link visibly across all viewports without hidden sm:flex", () => {
    render(
      <TopBar
        onToggleMobileSidebar={jest.fn()}
        onToggleDesktopSidebar={jest.fn()}
        isMobileSidebarOpen={false}
        isDesktopSidebarOpen={true}
      />
    );

    const homeLink = screen.getByRole("link", { name: "Home" });
    expect(homeLink).toBeInTheDocument();
    expect(homeLink).toHaveAttribute("href", "/dashboard/trades");
    expect(homeLink.className).toContain("flex");
    expect(homeLink.className).not.toContain("hidden");

    expect(screen.getByTestId("portfolio-switcher")).toBeInTheDocument();
    expect(screen.getByTestId("user-badge")).toBeInTheDocument();
  });
});
