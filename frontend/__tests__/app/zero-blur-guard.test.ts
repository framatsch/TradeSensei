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
 * @jest-environment node
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const roots = [join(process.cwd(), "app"), join(process.cwd(), "components"), join(process.cwd(), "lib")];

/** docs/DESIGN.md v2.0: Zero-Blur, no orbs, no glass utilities, GPU-friendly transitions only. */
const FORBIDDEN = [
  "backdrop-filter", "backdrop-blur", "backdrop-saturate", "filter: blur", "filter: saturate",
  "ambient-orbs", "orb-drift", "--orb-", "--glass-",
  "glass-chrome", "glass-card", "glass-inset", "glass-float", "btn-glass", "transition-all",
];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap(name => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(css|ts|tsx)$/.test(name) ? [path] : [];
  });
}

it("keeps frontend/app, frontend/components and frontend/lib free of blur, orb and glass remnants", () => {
  const hits = roots.flatMap(dir => sourceFiles(dir)).flatMap(path => {
    const source = readFileSync(path, "utf8");
    return FORBIDDEN.filter(needle => source.includes(needle)).map(needle => `${relative(process.cwd(), path)}: ${needle}`);
  });
  expect(hits).toEqual([]);
});
