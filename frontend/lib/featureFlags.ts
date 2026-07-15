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

export type FeatureFlagKey =
  | "risk_analytics";

export const FEATURE_FLAGS: { key: FeatureFlagKey; label: string; description: string; comingSoon?: boolean }[] = [
  {
    key: "risk_analytics",
    label: "Risk Analytics",
    description: "Unlocks the Risk Metrics tab in Analytics.",
  },
];

export const ALL_FEATURE_KEYS: FeatureFlagKey[] = FEATURE_FLAGS.map((f) => f.key);
