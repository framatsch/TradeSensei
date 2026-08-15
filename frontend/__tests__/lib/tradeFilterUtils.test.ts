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

import { buildDefinitionFromFilters, definitionToSearchParams } from "@/lib/tradeFilterUtils";

describe("tradeFilterUtils execution_state", () => {
  it("serializes execution_state into URLSearchParams", () => {
    const params = definitionToSearchParams({ execution_state: ["manual", "imported"] });
    expect(params.get("execution_state")).toBe("manual,imported");
  });

  it("keeps execution_state in saved definition", () => {
    const definition = buildDefinitionFromFilters({ execution_state: ["edited"] });
    expect(definition.execution_state).toEqual(["edited"]);
  });

  it("round-trips has_unlinked_executions in URL params and saved definition", () => {
    const params = definitionToSearchParams({ has_unlinked_executions: true });
    expect(params.get("has_unlinked_executions")).toBe("true");

    const definition = buildDefinitionFromFilters({ has_unlinked_executions: true });
    expect(definition.has_unlinked_executions).toBe(true);
  });

  it("keeps has_unlinked_executions inactive when saved view omits the key", () => {
    const params = definitionToSearchParams({ execution_state: ["manual"] });
    expect(params.get("has_unlinked_executions")).toBeNull();

    const definition = buildDefinitionFromFilters({ execution_state: ["manual"] });
    expect(definition.has_unlinked_executions).toBeUndefined();
  });
});
