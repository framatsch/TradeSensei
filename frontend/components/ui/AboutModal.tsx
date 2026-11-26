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

"use client";

import { Logo } from "./Logo";

interface AboutModalProps {
  isOpen: boolean;
  onClose: () => void;
  version?: string;
  appName?: string;
  license?: string;
}

export function AboutModal({
  isOpen,
  onClose,
  version = "1.0.0",
  appName = "Trade Sensei",
  license = "AGPL-3.0",
}: AboutModalProps) {
  if (!isOpen) return null;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-overlay p-4"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`About ${appName}`}
        className="panel-float flex w-full max-w-sm flex-col items-center p-8 text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-6 transform transition-transform duration-300 hover:scale-105">
          <Logo size={120} className="rounded-2xl border-none" />
        </div>

        <h2 className="mb-1 text-2xl font-bold text-foreground">{appName}</h2>
        <p className="mb-6 text-sm font-medium text-muted-foreground">
          Statistical Analysis &amp; Visualization
        </p>

        <div className="panel-sub mb-6 w-full space-y-3 p-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Version</span>
            <span className="rounded border border-border bg-card px-2 py-0.5 font-mono font-semibold text-foreground">
              {version}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">License</span>
            <a
              href="https://github.com/framatsch/TradeSensei/blob/main/LICENSE"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-foreground underline"
            >
              {license}
            </a>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="btn-primary w-full py-2.5"
        >
          Close
        </button>

        <p className="mt-6 flex w-full items-center justify-between text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          <span>
            &copy; {new Date().getFullYear()} {appName}
          </span>
          <span className="flex items-center">
            <a
              href="https://github.com/framatsch/TradeSensei"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label="GitHub Repository"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="h-4 w-4"
                aria-hidden="true"
              >
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.63-5.37-12-12-12z" />
              </svg>
            </a>
          </span>
        </p>
      </div>
    </div>
  );
}
