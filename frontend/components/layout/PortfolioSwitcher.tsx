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

"use client";

import { useActivePortfolio } from "@/hooks/useActivePortfolio";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Check, ChevronDown } from "lucide-react";

export function PortfolioSwitcher() {
  const { activePortfolio, portfolios, isLoading, setActivePortfolio } = useActivePortfolio();

  if (isLoading) {
    return (
      <div className="h-8 w-48 rounded-md bg-muted animate-pulse flex items-center px-3" />
    );
  }

  if (!activePortfolio) return null;

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button data-testid="portfolio-switcher" className="flex items-center gap-2 h-8 px-2 rounded-md hover:bg-muted transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <div
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: activePortfolio.color_hex || "#6b7280" }}
          />
          <span className="font-medium text-sm truncate max-w-[150px]">
            {activePortfolio.name}
          </span>
          <span className="text-xs text-muted-foreground">{activePortfolio.base_currency}</span>
          
          <ChevronDown className="w-4 h-4 text-muted-foreground opacity-50 ml-1" />
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="center"
          className="z-50 w-64 p-1 bg-popover border border-border rounded-md shadow-md outline-none animate-in data-[side=bottom]:slide-in-from-top-2 data-[side=top]:slide-in-from-bottom-2"
        >
          {portfolios.map((portfolio) => (
            <DropdownMenu.Item
              key={portfolio.id}
              onClick={() => setActivePortfolio(portfolio.id)}
              className="flex items-center gap-2 w-full p-2 text-sm rounded-sm outline-none cursor-pointer hover:bg-muted focus:bg-muted relative"
            >
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: portfolio.color_hex || "#6b7280" }}
              />
              <span className="flex-1 truncate">{portfolio.name}</span>
              <span className="text-xs text-muted-foreground">{portfolio.base_currency}</span>
              
              {activePortfolio.id === portfolio.id && (
                <Check className="w-4 h-4 ml-1 text-primary absolute right-2" />
              )}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
