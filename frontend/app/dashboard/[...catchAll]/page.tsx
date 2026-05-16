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

import { redirect } from "next/navigation";

/**
 * Catch-all route for unknown paths under /dashboard/*.
 * Redirects to the dashboard overview instead of showing a 404.
 * Explicit routes (trades, analytics, cash, etc.) take precedence over
 * this catch-all and are never affected.
 */
export default function DashboardCatchAll() {
  redirect("/dashboard");
}
