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
 * ImportLogLine — a single color-coded line inside an import/sync activity log
 * panel. Shared between FileQueue (file upload) and ImportForm (API sync) so the
 * color coding stays consistent and isn't duplicated across the two panels.
 */

type LogLineCategory = "created" | "protected" | "other";

/**
 * Categorizes a log line by its message prefix. Works for both `activity_log`
 * entries (routine "created:"/"updated:"/"skipped:" lines) and `warnings`
 * entries (genuine protection warnings) — anything that doesn't match a known
 * informational prefix falls back to "other", which is the correct treatment
 * for a genuine warning line too.
 */
function categorizeLogLine(line: string): LogLineCategory {
  if (line.startsWith("created:")) return "created";
  if (line.startsWith("protected_")) return "protected";
  return "other";
}

const LOG_LINE_COLOR: Record<LogLineCategory, string> = {
  created: "text-success",
  protected: "text-primary",
  other: "text-warning",
};

interface ImportLogLineProps {
  text: string;
}

export function ImportLogLine({ text }: ImportLogLineProps) {
  return (
    <div className={`flex items-start gap-2 ${LOG_LINE_COLOR[categorizeLogLine(text)]}`}>
      <span className="text-muted-foreground select-none">▶</span>
      <span>{text}</span>
    </div>
  );
}
