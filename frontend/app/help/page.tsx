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
 * Help page — Metric & feature glossary for Trade Sensei.
 * Each section has an id anchor so MetricHelpLink can jump directly to it.
 * Layout: sticky TOC on the left, scrollable content on the right.
 *
 * Content is sourced from frontend/lib/help-content.ts (single source of truth).
 * The same dictionary is used by tools/export_help.ts to generate the Markdown export.
 */

import type { Metadata } from "next";
import { HelpClient } from "./HelpClient";
import { HELP_SECTIONS } from "@/lib/help-content";
import { version } from "../../package.json";

export const metadata: Metadata = {
  title: "Help & Reference — Trade Sensei",
};

export default function HelpPage() {
  return <HelpClient sections={HELP_SECTIONS} version={version} />;
}
