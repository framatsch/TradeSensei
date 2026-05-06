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
