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

/**
 * Settings page — unified hub for user preferences, accounts, and broker integrations.
 *
 * Tabs:
 * - General: theme, default date range
 * - Accounts & Integrations: trading accounts + broker connections (Schwab, IBKR)
 */

import { Suspense } from "react";
import { Spinner } from "@/components/ui/Spinner";
import { SettingsPageClient } from "./SettingsPageClient";

export const metadata = {
  title: "Settings — Trade Sensei",
};

export default function SettingsPage() {
  return (
    <>
      <Suspense
        fallback={
          <div className="flex items-center justify-center h-64">
            <Spinner size="lg" />
          </div>
        }
      >
        <SettingsPageClient />
      </Suspense>
    </>
  );
}
