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
import { readFileSync } from "node:fs";
import { join } from "node:path";

const css = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");
const design = readFileSync(join(process.cwd(), "../docs/DESIGN.md"), "utf8");
const light = css.match(/\n:root\s*\{([\s\S]*?)\n\}/)?.[1] ?? "";
const dark = css.match(/\nhtml\.dark\s*\{([\s\S]*?)\n\}/)?.[1] ?? "";

/** The production-ready token block in docs/DESIGN.md section 6. */
const designBlock = design.match(/## 6\.[\s\S]*?```css\n([\s\S]*?)```/)?.[1] ?? "";
const designLight = designBlock.match(/:root\s*\{([\s\S]*?)\n\}/)?.[1] ?? "";
const designDark = designBlock.match(/\.dark\s*\{([\s\S]*?)\n\}/)?.[1] ?? "";
const declarations = (block: string) =>
  [...block.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map(([, name, value]) => [name, value.trim()] as const);
const valueOf = (block: string, name: string) =>
  block.match(new RegExp(`\\n\\s*${name}:\\s*([^;]+);`))?.[1]?.trim() ?? null;

describe("docs/DESIGN.md section 6 token block", () => {
  it("is found and defines the same number of tokens for both themes", () => {
    expect(declarations(designLight).length).toBeGreaterThanOrEqual(39);
    expect(declarations(designDark).length).toBe(declarations(designLight).length);
  });
});

describe("globals.css matches docs/DESIGN.md 1:1", () => {
  it.each(declarations(designLight))("Light defines %s: %s", (name, value) => {
    expect({ theme: "light", name, value: valueOf(light, name) }).toEqual({ theme: "light", name, value });
  });

  it.each(declarations(designDark))("Dark defines %s: %s", (name, value) => {
    expect({ theme: "dark", name, value: valueOf(dark, name) }).toEqual({ theme: "dark", name, value });
  });

  it("defines the single-layer float shadow in both themes", () => {
    expect(valueOf(light, "--float-shadow")).toBe("0 8px 24px rgba(15, 23, 42, 0.12)");
    expect(valueOf(dark, "--float-shadow")).toBe("0 8px 24px rgba(0, 0, 0, 0.40)");
  });
});

describe("globals.css theme rules", () => {
  it("has no html.dark override selectors for buttons, status surfaces or rows", () => {
    expect(css).not.toMatch(/html\.dark\s+\.(btn-|surface-|wl-row)/);
  });

  it("drives the chart grid and tooltip from tokens", () => {
    expect(css).toMatch(/\.recharts-cartesian-grid line[,\s\S]*?\{[^}]*var\(--chart-grid\)/);
    expect(css).toMatch(/\.recharts-default-tooltip[,\s\S]*?\{[^}]*var\(--bg-panel\)/);
  });

  it("keeps the semantic bridge tokens as hex literals for contrast", () => {
    for (const name of ["--background", "--foreground", "--card", "--primary", "--primary-foreground", "--danger"]) {
      expect({ name, light: valueOf(light, name) }).toEqual({ name, light: expect.stringMatching(/^#[\da-fA-F]{6}$/) });
      expect({ name, dark: valueOf(dark, name) }).toEqual({ name, dark: expect.stringMatching(/^#[\da-fA-F]{6}$/) });
    }
  });
});
