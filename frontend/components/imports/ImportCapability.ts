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

import type { AccountType } from "@/lib/types";

export type BrokerImportCapability = {
  maxWindowDays: number;
  syncParam: { kind: "fromDate" } | { kind: "days" };
};

const CAPABILITY_MAP: Record<AccountType, BrokerImportCapability> = {
  ibkr: { maxWindowDays: 365, syncParam: { kind: "fromDate" } },
  schwab: { maxWindowDays: 365, syncParam: { kind: "days" } },
  manual: { maxWindowDays: 0, syncParam: { kind: "days" } },
};

export function capabilityFor(accountType: AccountType): BrokerImportCapability {
  return CAPABILITY_MAP[accountType];
}
